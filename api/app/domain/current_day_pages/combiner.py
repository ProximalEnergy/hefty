import datetime
from typing import Annotated

import pandas as pd
from core.enumerations import DeviceType
from fastapi import Depends
from natsort import natsorted
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from core import models


def get_equipment_analysis_combiner_data(
    *,
    project_db: Session,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """todo

    Args:
        project_db: TODO: describe.
        project: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
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

    # Get combiner devices
    devices_combiner = core.crud.project.devices.get_project_devices(
        project_db,
        device_type_ids=[DeviceType.PV_DC_COMBINER],
    ).models()

    # Get combiner current tags
    tags_combiner_current = core.crud.project.tags.get_project_tags(
        project_db,
        in_tsdb=True,
        sensor_type_name_shorts=["pv_dc_combiner_current"],
    ).models()

    device_id_to_device: dict[int, models.Device] = {
        device.device_id: device for device in devices_combiner
    }

    tag_id_to_combiner_name_long: dict[int, str] = {
        tag.tag_id: (device_id_to_device[tag.device_id].name_long or "NO NAME LONG")
        for tag in tags_combiner_current
    }
    tag_id_to_combiner_capacity_dc: dict[int, float] = {
        tag.tag_id: (device_id_to_device[tag.device_id].capacity_dc or 1)
        for tag in tags_combiner_current
    }

    # Get combiner current data
    df = utils.data_df(
        project_db,
        project,
        tags=tags_combiner_current,
        start=start,
        end=end,
        fillna_zero=False,
    )

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
    x, y, y_norm = zip(*natsorted(zip(x, y, y_norm)))  # type: ignore

    return_data = {
        "x": x,
        "y": y,
        "y_norm": y_norm,
    }

    return return_data
