from typing import Annotated
from uuid import UUID

import numpy as np
import pandas as pd
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import DeviceType, SensorType
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import core
from app import dependencies, interfaces, utils
from app.utils import get_include_in_schema
from core import models

router = APIRouter(
    prefix="/combiner",
    tags=["gis"],
    dependencies=[Depends(dependencies.check_project_access_async)],
    include_in_schema=get_include_in_schema(),
)


@router.get(
    "/{project_id}/{block_device_id}",
    response_model=interfaces.GeoJSON,
)
async def get_combiner_block_performance(
    *,
    project_id: UUID,
    block_device_id: int,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    # Query data for the last 30 minutes (offset by 5 minutes)
    """todo

    Args:
        project_id: Description for project_id.
        block_device_id: Description for block_device_id.
        project_db: Description for project_db.
        project: Description for project.
    """
    _ = project_id
    end = pd.Timestamp.utcnow().floor("5min")
    start = end - pd.Timedelta(minutes=30)

    # Get requested pv_block device
    project_schema = utils.get_project_schema(project_db=project_db)
    device_block_df = await core.crud.project.devices.get_project_device(
        device_id=block_device_id,
        deep=False,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if device_block_df.empty:
        raise HTTPException(
            status_code=404,
            detail="Block device not found",
        )
    device_block = device_block_df.to_dict("records")[0]

    # Get descendent pv_dc_combiner devices of requests pv_block
    devices_combiner_df = await core.crud.project.devices.get_project_devices(
        device_type_ids=[DeviceType.PV_DC_COMBINER],
        device_id_descendent_of=int(device_block["device_id"]),
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    # Get tags for combiner current
    tags_df = await core.crud.project.tags.get_project_tags_v2(
        sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT],
        device_ids=devices_combiner_df["device_id"].astype(int).tolist(),
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    # Get data for combiner current
    missing_data = False

    data = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=tags_df["tag_id"].astype(int).tolist(),
        query_start=start,
        query_end=end,
        project_db=project_db,
    ).get()

    df = data.df.to_pandas()
    df = df.set_index("time")
    df.columns = df.columns.astype(int)

    # Drop all rows that have all NaNs
    df = df.dropna(how="all")

    if len(df) == 0:
        missing_data = True

    if not missing_data:
        # Rename columns from tags to device ids
        # NOTE: These device ids are combiner device ids
        tag_id_to_device_id = dict(
            zip(
                tags_df["tag_id"].astype(int),
                tags_df["device_id"].astype(int),
                strict=True,
            ),
        )
        df = df.rename(columns=lambda tag_id: tag_id_to_device_id[int(tag_id)])

        timestamp = df.index[-1].isoformat()
        max_current = df.tail(1).max().max()

    else:
        timestamp = (end - pd.Timedelta(minutes=5)).isoformat()
        max_current = 1

    features = [
        {
            "type": "Feature",
            "properties": {
                "timestamp": timestamp,
                # TODO: This needs to be better than just grabbing the last value
                "combiner_current": (
                    df[device["device_id"]].iloc[-1] if not missing_data else np.nan
                ),
                "combiner_name": device.get("name_long"),
                "block_name": device_block["name_long"],
                "max_current": max_current,
            },
            "geometry": interfaces.convert(WKBElement=device.get("polygon")),
        }
        for device in devices_combiner_df.to_dict("records")
    ]

    return_data = {
        "type": "FeatureCollection",
        "features": features,
    }

    return return_data
