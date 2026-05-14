import datetime
from typing import Annotated

from core.crud.project import devices as project_devices
from core.crud.project import tags as project_tags
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import DeviceTypeEnum, KPITypeEnum, SensorTypeEnum
from fastapi import Depends, HTTPException
from natsort import natsorted
from sqlalchemy.orm import Session

from app import dependencies, utils
from app.v1.operational.kpi_data import get_kpi_data_helper
from core import models


async def get_tracker_data(
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
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_df = await project_devices.get_project_devices(
        device_type_ids=[
            DeviceTypeEnum.PV_BLOCK,
            DeviceTypeEnum.TRACKER_ROW,
        ],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    devices_df = devices_df.copy()
    devices_df["device_type_id"] = devices_df["device_type_id"].astype(int)

    # Create lookup mappings
    device_id_to_name_long = dict(
        zip(
            devices_df["device_id"].astype(int),
            devices_df["name_long"].fillna(""),
        )
    )
    block_device_id_to_tracker_row_ids = utils.map_ancestors_to_descendents(
        ancestors=devices_df[devices_df["device_type_id"] == DeviceTypeEnum.PV_BLOCK],
        descendents=devices_df[
            devices_df["device_type_id"] == DeviceTypeEnum.TRACKER_ROW
        ],
    )

    # Get KPI data
    kpi_data_dict = utils.kpi_data_list_to_dict(
        kpi_data=await get_kpi_data_helper(
            start=start,
            end=end,
            kpi_type_ids=[
                KPITypeEnum.TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_BLOCK,
                KPITypeEnum.TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_BLOCK,
                KPITypeEnum.TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_ROW,
                KPITypeEnum.TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_ROW,
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


async def get_tracker_by_pv_block_id_data(
    *,
    pv_block_id: int,
    project: models.Project,
    project_db: Session,
    start: datetime.datetime,
    end: datetime.datetime,
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
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_df = await project_devices.get_project_devices(
        device_type_ids=[DeviceTypeEnum.TRACKER_ROW],
        device_id_descendent_of=pv_block_id,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    # Get all position and setpoint tags for the tracker rows
    tags = await project_tags.get_project_tags_v2(
        device_ids=devices_df["device_id"].astype(int).tolist(),
        sensor_type_ids=[
            SensorTypeEnum.TRACKER_ROW_POSITION,
            SensorTypeEnum.TRACKER_ROW_SETPOINT,
        ],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    # Query tracker position and setpoint data
    data = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=tags["tag_id"].astype(int).tolist(),
        query_start=start,
        query_end=end,
        project_db=project_db,
    ).get()

    df = data.df.to_pandas()
    df = df.set_index("time")
    df.columns = df.columns.astype(int)

    device_id_to_name_long = dict(
        zip(
            devices_df["device_id"].astype(int),
            devices_df["name_long"].fillna(""),
        )
    )
    tag_id_to_device_name_long = {
        int(tag_id): device_id_to_name_long[int(device_id)]
        for tag_id, device_id in zip(tags["tag_id"], tags["device_id"])
    }

    tags_ids_position = natsorted(
        tags.loc[
            tags["sensor_type_id"] == SensorTypeEnum.TRACKER_ROW_POSITION,
            "tag_id",
        ]
        .astype(int)
        .tolist()
    )
    tags_ids_setpoint = natsorted(
        tags.loc[
            tags["sensor_type_id"] == SensorTypeEnum.TRACKER_ROW_SETPOINT,
            "tag_id",
        ]
        .astype(int)
        .tolist()
    )

    df_position = df[tags_ids_position]
    df_setpoint = df[tags_ids_setpoint]

    return {
        "times": df.index.tolist(),
        "positions": {
            tag_id_to_device_name_long[tag_id]: df_position[tag_id].tolist()
            for tag_id in tags_ids_position
        },
        "setpoints": {
            tag_id_to_device_name_long[tag_id]: df_setpoint[tag_id].tolist()
            for tag_id in tags_ids_setpoint
        },
    }
