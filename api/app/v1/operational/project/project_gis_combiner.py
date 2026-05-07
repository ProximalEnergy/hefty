from typing import Annotated

import numpy as np
import pandas as pd
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import DeviceTypeEnum, SensorTypeEnum
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import interfaces, utils
from app.dependencies import get_project_api, get_project_db
from core import crud, models

router = APIRouter(
    prefix="/gis",
    tags=["gis"],
)


@router.get(
    "/combiner/{block_device_id}",
    response_model=interfaces.GeoJSON,
)
async def get_combiner_block_performance(
    *,
    block_device_id: int,
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
):
    """Get combiner performance at the block level.

    Args:
        block_device_id: The device ID of the PV block to query combiners for.
        project_db: Database session for the project's schema.
        project: The project model resolved via dependency injection.
    """
    end = pd.Timestamp.now("UTC").floor("5min")
    start = end - pd.Timedelta(minutes=30)

    # Get requested pv_block device
    project_schema = utils.get_project_schema(project_db=project_db)
    device_block_df = await crud.project.devices.get_project_device(
        device_id=block_device_id,
        deep=False,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if device_block_df.empty:
        raise HTTPException(
            status_code=404,
            detail="Block device not found",
        )
    device_block = device_block_df.to_dict("records")[0]

    # Get descendent pv_dc_combiner devices of requested pv_block
    devices_combiner_df = await crud.project.devices.get_project_devices(
        device_type_ids=[DeviceTypeEnum.PV_DC_COMBINER],
        device_id_descendent_of=int(device_block["device_id"]),
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    # Get tags for combiner current
    tags_df = await crud.project.tags.get_project_tags_v2(
        sensor_type_ids=[SensorTypeEnum.PV_DC_COMBINER_CURRENT],
        device_ids=devices_combiner_df["device_id"].astype(int).tolist(),
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

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
        # Rename columns from tag ids to device ids
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

    return {
        "type": "FeatureCollection",
        "features": features,
    }
