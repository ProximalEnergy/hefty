from typing import Annotated
from uuid import UUID

import numpy as np
import pandas as pd
from core.db_query import OutputType
from core.enumerations import DeviceType, SensorType
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import ORJSONResponse
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
    response_class=ORJSONResponse,
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
        project_id: TODO: describe.
        block_device_id: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
    """
    end = pd.Timestamp.utcnow().floor("5min")
    start = end - pd.Timedelta(minutes=30)

    # Get requested pv_block device
    schema_translate_map = (
        project_db.get_bind().get_execution_options().get("schema_translate_map", {})
    )
    project_schema = schema_translate_map.get("project")
    device_block = await core.crud.project.devices.get_project_device(
        device_id=block_device_id,
        deep=False,
    ).get_async(output_type=OutputType.SQLALCHEMY, schema=project_schema)

    if device_block is None:
        raise HTTPException(
            status_code=404,
            detail="Block device not found",
        )

    # Get descendent pv_dc_combiner devices of requests pv_block
    devices_combiner = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_type_ids=[DeviceType.PV_DC_COMBINER],
        device_id_descendent_of=device_block.device_id,
    ).models()

    # Get tags for combiner current
    tags = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT],
        device_ids=[d.device_id for d in devices_combiner],
    ).models()

    # Get data for combiner current
    try:
        df = utils.data_df(
            project_db,
            project,
            tags,
            start=start,
            end=end,
            fillna_zero=False,
        )
        missing_data = False

        # Drop all rows that have all NaNs
        df = df.dropna(how="all")

        if len(df) == 0:
            missing_data = True
    except HTTPException:
        missing_data = True

    if not missing_data:
        # Rename columns from tags to device ids
        # NOTE: These device ids are combiner device ids
        tag_id_to_device_id = {tag.tag_id: tag.device_id for tag in tags}
        df.columns = pd.Index(
            [tag_id_to_device_id[tag_id] for tag_id in df.columns.astype(int)],
        )

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
                    df[device.device_id].iloc[-1] if not missing_data else np.nan
                ),
                "combiner_name": device.name_long,
                "block_name": device_block.name_long,
                "max_current": max_current,
            },
            "geometry": device.polygon,
        }
        for device in devices_combiner
    ]

    return_data = {
        "type": "FeatureCollection",
        "features": features,
    }

    return return_data
