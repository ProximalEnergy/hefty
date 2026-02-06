import datetime
from typing import Annotated

import pandas as pd
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import DeviceType, SensorType
from fastapi import Depends, HTTPException
from natsort import natsorted
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from core import models


async def get_equipment_analysis_combiner_data(
    *,
    project_db: Session,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """Return combiner current data for the requested interval.

    Args:
        project_db: Database session for the project's schema.
        project: Project model from the request context.
        start: Optional start datetime for the window.
        end: Optional end datetime for the window.
    """
    mean = False
    if start is None and end is None:
        # Define start and end times
        end = pd.Timestamp.utcnow().floor("5min")
        start = end - pd.Timedelta(minutes=15)
    elif start and end:
        mean = True
        start = (
            pd.Timestamp(start)
            .tz_convert(project.time_zone)
            .replace(hour=11, minute=30)
        )
        end = (
            pd.Timestamp(end).tz_convert(project.time_zone).replace(hour=12, minute=30)
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either both start and end must be provided or neither.",
        )

    # Get combiner devices
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_combiner_df = await core.crud.project.devices.get_project_devices(
        device_type_ids=[DeviceType.PV_DC_COMBINER],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    devices_combiner_df = devices_combiner_df.copy()
    devices_combiner_df["name_long"] = devices_combiner_df["name_long"].fillna("")
    devices_combiner_df["capacity_dc"] = devices_combiner_df["capacity_dc"].fillna(1)

    # Get combiner current tags
    tags_combiner_current = await core.crud.project.tags.get_project_tags_v2(
        in_tsdb=True,
        sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    device_id_to_device = {
        int(device["device_id"]): device
        for device in devices_combiner_df.to_dict("records")
    }

    tag_id_to_combiner_name_long: dict[int, str] = {}
    tag_id_to_combiner_capacity_dc: dict[int, float] = {}
    for tag_id, device_id in zip(
        tags_combiner_current["tag_id"],
        tags_combiner_current["device_id"],
    ):
        tag_id_int = int(tag_id)
        device = device_id_to_device[int(device_id)]
        tag_id_to_combiner_name_long[tag_id_int] = (
            device.get("name_long") or "NO NAME LONG"
        )
        tag_id_to_combiner_capacity_dc[tag_id_int] = device.get("capacity_dc") or 1

    # Get combiner current data
    data = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=tags_combiner_current["tag_id"].astype(int).tolist(),
        query_start=start,
        query_end=end,
        project_db=project_db,
    ).get()

    df = data.df.to_pandas()
    df = df.set_index("time")
    df.columns = df.columns.astype(int)

    # Drop rows that have all NaN
    df = df.dropna(how="all")

    x = [tag_id_to_combiner_name_long[int(tag_id)] for tag_id in df.columns]
    if mean:
        y = df.mean().fillna(0).values.tolist()
    else:
        if df.empty:
            y = [0] * len(df.columns)
        else:
            y = df.tail(1).fillna(0).values.tolist()[0]
    y_norm = [
        y / tag_id_to_combiner_capacity_dc[int(tag_id)]
        for tag_id, y in zip(df.columns, y)
    ]

    # Sort both x and y by x
    if not x:  # If x is empty, y and y_norm will also be empty
        x, y, y_norm = [], [], []
    else:
        x, y, y_norm = [list(t) for t in zip(*natsorted(zip(x, y, y_norm)))]

    return_data = {
        "x": x,
        "y": y,
        "y_norm": y_norm,
    }

    return return_data
