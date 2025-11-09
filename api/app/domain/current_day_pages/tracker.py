import datetime
from typing import Annotated

import pandas as pd
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from app.v1.operational.kpi_data import get_kpi_data_helper
from core import models


def get_tracker_data(
    *,
    start: datetime.date,
    end: datetime.date,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    """
    Retrieves tracker data for a given project.

    Args:
        start: The start date for the data query.
        end: The end date for the data query.
        project_db: The project database session.
        project: The project model.

    Returns:
        A dictionary containing tracker data.
    """
    # Get devices
    devices = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_type_ids=[
            6,  # block (PV Block)
            29,  # tracker_row (Tracker Row)
        ],
    ).models()

    # Create lookup mappings
    device_id_to_name_long = {d.device_id: d.name_long for d in devices}
    block_device_id_to_tracker_row_ids = utils.map_ancestors_to_descendents(
        ancestors=[d for d in devices if d.device_type_id == 6],
        descendents=[d for d in devices if d.device_type_id == 29],
    )

    # Get KPI data
    kpi_data_dict = utils.kpi_data_list_to_dict(
        kpi_data=get_kpi_data_helper(
            db=project_db,
            start=start,
            end=end,
            kpi_type_ids=[
                18,  # tracker_position_deviating_from_setpoint_by_block
                19,  # tracker_setpoint_deviating_from_median_by_block
                21,  # tracker_position_deviating_from_setpoint_by_row
                22,  # tracker_setpoint_deviating_from_median_by_row
            ],
            project_ids=[project.project_id],
            include_device_data=True,
        ),
        key="kpi_type_id",
    )

    # Look for KPI data by KPI type id
    kpi_data_pos_block = kpi_data_dict.get(18)
    kpi_data_sp_block = kpi_data_dict.get(19)
    kpi_data_pos_row = kpi_data_dict.get(21)
    kpi_data_sp_row = kpi_data_dict.get(22)

    # If any KPI data is not found, raise an error
    if any(
        kpi_data is None
        for kpi_data in [
            kpi_data_pos_block,
            kpi_data_sp_block,
            kpi_data_pos_row,
            kpi_data_sp_row,
        ]
    ):
        raise HTTPException(status_code=404, detail="No data found")

    # Parse KPI data to a DataFrame and take the mean
    s_pos_block = utils.parse_kpi_data_to_df(kpi_data=kpi_data_pos_block).mean()  # type: ignore
    s_pos_block.index = s_pos_block.index.astype(int)
    s_sp_block = utils.parse_kpi_data_to_df(kpi_data=kpi_data_sp_block).mean()  # type: ignore
    s_sp_block.index = s_sp_block.index.astype(int)
    s_pos_row = utils.parse_kpi_data_to_df(kpi_data=kpi_data_pos_row).mean()  # type: ignore
    s_pos_row.index = s_pos_row.index.astype(int)
    s_sp_row = utils.parse_kpi_data_to_df(kpi_data=kpi_data_sp_row).mean()  # type: ignore
    s_sp_row.index = s_sp_row.index.astype(int)

    s_pos_block.index = s_pos_block.index.map(device_id_to_name_long)
    s_pos_block = s_pos_block.sort_index()
    s_sp_block.index = s_sp_block.index.map(device_id_to_name_long)
    s_sp_block = s_sp_block.sort_index()

    return {
        "position_from_setpoint": {
            "by_block": s_pos_block.to_dict(),
            "by_row": {
                device_id_to_name_long[block_device_id]: {
                    device_id_to_name_long[row_device_id]: s_pos_row.loc[row_device_id]
                    for row_device_id in block_device_id_to_tracker_row_ids[
                        block_device_id
                    ]
                }
                for block_device_id in block_device_id_to_tracker_row_ids
            },
        },
        "setpoint_from_median": {
            "by_block": s_sp_block.to_dict(),
            "by_row": {
                device_id_to_name_long[block_device_id]: {
                    device_id_to_name_long[row_device_id]: s_sp_row.loc[row_device_id]
                    for row_device_id in block_device_id_to_tracker_row_ids[
                        block_device_id
                    ]
                }
                for block_device_id in block_device_id_to_tracker_row_ids
            },
        },
    }


def get_tracker_by_pv_block_id_data(
    *,
    pv_block_id: int,
    project: models.Project,
    project_db: Session,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """
    Retrieves tracker data for a given PV block.

    Args:
        pv_block_id: The ID of the PV block.
        project: The project model.
        project_db: The project database session.
        start: The start datetime for the data query.
        end: The end datetime for the data query.

    Returns:
        A dictionary containing tracker data for the specified PV block.
    """
    # Get tracker rows that are descendants of the pv block
    devices = core.crud.project.devices.get_project_devices(
        project_db,
        device_type_ids=[29],  # Tracker Zone (tracker_zone)
        device_id_descendent_of=pv_block_id,
    ).models()

    # Get all position and setpoint tags for the tracker rows
    tags = core.crud.project.tags.get_project_tags(
        db=project_db,
        device_ids=[d.device_id for d in devices],
        sensor_type_ids=[
            24,  # tracker_position
            25,  # tracker_setpoint
        ],
    ).models()

    # Query tracker position and setpoint data
    df = utils.data_df(
        project_db=project_db,
        project=project,
        tags=tags,
        start=start,
        end=end,
        fillna_zero=False,
    )

    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)

    device_id_to_name_short = {d.device_id: d.name_short for d in devices}
    tag_id_to_device_name_short = {
        t.tag_id: device_id_to_name_short[t.device_id] for t in tags
    }

    tags_ids_position = [t.tag_id for t in tags if t.sensor_type_id == 24]
    tags_ids_setpoint = [t.tag_id for t in tags if t.sensor_type_id == 25]

    df_position = df[tags_ids_position]
    df_setpoint = df[tags_ids_setpoint]

    return {
        "times": df.index.tolist(),
        "positions": {
            tag_id_to_device_name_short[tag_id]: df_position[tag_id].tolist()
            for tag_id in tags_ids_position
        },
        "setpoints": {
            tag_id_to_device_name_short[tag_id]: df_setpoint[tag_id].tolist()
            for tag_id in tags_ids_setpoint
        },
    }
