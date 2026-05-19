import datetime
import logging
from typing import Annotated, Literal, TypedDict

import numpy as np
import pandas as pd
import polars as pl
from core.crud.operational.device_types import get_device_types as crud_get_device_types
from core.crud.project import data_timeseries_last as project_data_timeseries_last
from core.crud.project import devices as project_devices
from core.crud.project import tags as project_tags
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import DeviceTypeEnum, TimeOffset
from core.enumerations import SensorTypeEnum as SensorTypeEnum
from fastapi import APIRouter, Depends, HTTPException, Query
from natsort import natsorted
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import dependencies, utils
from app._dependencies.filtering import filter_start_datetime_to_data_access_start_time
from app._utils.arrow import polars_to_arrow_response
from app.interfaces import normalize_pandas_nullable
from core import models

router = APIRouter(
    prefix="/device-details",
    tags=["device-details"],
    include_in_schema=utils.get_include_in_schema(),
)


def _get_sorted_horizontal_device_data(
    *,
    df: pd.DataFrame,
    category: str,
    tag_id_to_category: dict[int, str],
    tag_id_to_device_name_long: dict[int, str | None],
    tag_id_to_device_id: dict[int, int],
):
    """Filter columns by category and return device data sorted by name.

    Args:
        df: DataFrame whose columns are tag IDs and rows are time-series
            values.
        category: The category string used to filter tag IDs.
        tag_id_to_category: Mapping from tag ID to its category label.
        tag_id_to_device_name_long: Mapping from tag ID to the human-readable
            device name, or None if unavailable.
        tag_id_to_device_id: Mapping from tag ID to the corresponding device
            ID.
    """
    data = [
        {
            "values": df[int(c)].tolist(),
            "name": tag_id_to_device_name_long[int(c)],
            "device_id": tag_id_to_device_id[int(c)],
        }
        for c in df.columns.astype(int)
        if tag_id_to_category[int(c)] == category
    ]

    return natsorted(data, key=lambda x: x["name"])


def _get_sorted_vertical_device_data(
    *,
    df: pd.DataFrame,
    tag_id_to_device_name_long: dict[int, str],
    tag_id_to_device_id: dict[int, int],
):
    """Return device data for all columns sorted by device name.

    Args:
        df: DataFrame whose columns are tag IDs and rows are time-series
            values.
        tag_id_to_device_name_long: Mapping from tag ID to the human-readable
            device name.
        tag_id_to_device_id: Mapping from tag ID to the corresponding device
            ID.
    """
    data = [
        {
            "name": tag_id_to_device_name_long[int(c)],
            "values": df[int(c)].tolist(),
            "device_id": tag_id_to_device_id[int(c)],
        }
        for c in df.columns.astype(int)
    ]

    return natsorted(data, key=lambda x: x["name"])


@router.get("/horizontal/bess")
async def get_horizontal_bess(
    start: Annotated[
        datetime.datetime, Depends(filter_start_datetime_to_data_access_start_time)
    ],
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    """todo

    Args:
        start: Description for start.
        end: Description for end.
        project: Description for project.
        project_db: Description for project_db.
    """

    # Determine what is the "highest" level of battery storage data
    used_sensor_type_ids = project.spec.used_sensor_type_ids  # type: ignore
    if SensorTypeEnum.BESS_PCS_SOC_PERCENT in used_sensor_type_ids:
        bess_sensor_type_id = SensorTypeEnum.BESS_PCS_SOC_PERCENT
    elif SensorTypeEnum.BESS_ENCLOSURE_SOC_PERCENT in used_sensor_type_ids:
        bess_sensor_type_id = SensorTypeEnum.BESS_ENCLOSURE_SOC_PERCENT
    elif SensorTypeEnum.BESS_DC_SKID_SOC_PERCENT in used_sensor_type_ids:
        bess_sensor_type_id = SensorTypeEnum.BESS_DC_SKID_SOC_PERCENT
    elif SensorTypeEnum.BESS_BANK_SOC_PERCENT in used_sensor_type_ids:
        bess_sensor_type_id = SensorTypeEnum.BESS_BANK_SOC_PERCENT
    elif SensorTypeEnum.BESS_STRING_SOC_PERCENT in used_sensor_type_ids:
        bess_sensor_type_id = SensorTypeEnum.BESS_STRING_SOC_PERCENT
    else:
        bess_sensor_type_id = None

    # Configure sensor_type_ids based on the battery storage data level
    sensor_type_ids: list[int] = [
        SensorTypeEnum.METER_ACTIVE_POWER,
        SensorTypeEnum.PROJECT_SOC_PERCENT,
        SensorTypeEnum.BESS_PCS_AC_POWER,
    ]
    if bess_sensor_type_id is not None:
        sensor_type_ids.append(bess_sensor_type_id)

    project_schema = utils.get_project_schema(project_db=project_db)
    tags = await project_tags.get_project_tags_v2(
        sensor_type_ids=sensor_type_ids,
        deep=True,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    category_mapping: dict[int, str] = {
        SensorTypeEnum.METER_ACTIVE_POWER: "meter_power",
        SensorTypeEnum.PROJECT_SOC_PERCENT: "meter_soc",
        SensorTypeEnum.BESS_PCS_AC_POWER: "pcs",
        SensorTypeEnum.BESS_PCS_SOC_PERCENT: "battery",
        SensorTypeEnum.BESS_DC_SKID_SOC_PERCENT: "battery",
        SensorTypeEnum.BESS_ENCLOSURE_SOC_PERCENT: "battery",
        SensorTypeEnum.BESS_BANK_SOC_PERCENT: "battery",
        SensorTypeEnum.BESS_STRING_SOC_PERCENT: "battery",
    }

    tag_ids = tags["tag_id"].astype(int)
    tag_sensor_type_ids = tags["sensor_type_id"].fillna(-1).astype(int)
    device_name_long = normalize_pandas_nullable(
        content=tags["device_name_long"].tolist()
    )
    tag_id_to_device_name_long = dict(zip(tag_ids, device_name_long, strict=True))
    tag_id_to_category = dict(
        zip(tag_ids, tag_sensor_type_ids.map(category_mapping), strict=True)
    )
    tag_id_to_device_id = dict(zip(tag_ids, tags["device_id"].astype(int), strict=True))

    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=tag_ids.tolist(),
        query_start=start,
        query_end=end,
        project_db=project_db,
        max_lookback_period=TimeOffset.FIVE_MINUTES,
    ).get()

    df = data_timeseries_instance.df.to_pandas()
    df = df.set_index("time")
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
    df.columns = df.columns.astype(int)

    data_meter_power = _get_sorted_horizontal_device_data(
        df=df,
        category="meter_power",
        tag_id_to_category=tag_id_to_category,
        tag_id_to_device_name_long=tag_id_to_device_name_long,
        tag_id_to_device_id=tag_id_to_device_id,
    )
    data_meter_soc = _get_sorted_horizontal_device_data(
        df=df,
        category="meter_soc",
        tag_id_to_category=tag_id_to_category,
        tag_id_to_device_name_long=tag_id_to_device_name_long,
        tag_id_to_device_id=tag_id_to_device_id,
    )
    data_pcs = _get_sorted_horizontal_device_data(
        df=df,
        category="pcs",
        tag_id_to_category=tag_id_to_category,
        tag_id_to_device_name_long=tag_id_to_device_name_long,
        tag_id_to_device_id=tag_id_to_device_id,
    )
    data_battery = _get_sorted_horizontal_device_data(
        df=df,
        category="battery",
        tag_id_to_category=tag_id_to_category,
        tag_id_to_device_name_long=tag_id_to_device_name_long,
        tag_id_to_device_id=tag_id_to_device_id,
    )

    return {
        "times": df.index.tolist(),
        "meter_power": data_meter_power,
        "meter_soc": data_meter_soc,
        "pcs": data_pcs,
        "battery": data_battery,
    }


class DeviceDetailsHorizonalData(BaseModel):
    """todo"""

    values: list[float]
    name: str | None
    device_id: int


class DeviceDetailsHorizontalPV(BaseModel):
    """todo"""

    times: list[datetime.datetime]
    meter_power: list[DeviceDetailsHorizonalData]
    met: list[DeviceDetailsHorizonalData]
    pcs: list[DeviceDetailsHorizonalData]


@router.get(
    "/horizontal/pv",
    response_model=DeviceDetailsHorizontalPV,
)
async def get_horizontal_pv(
    start: datetime.datetime,
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    """todo

    Args:
        start: Description for start.
        end: Description for end.
        project: Description for project.
        project_db: Description for project_db.
    """
    sensor_type_ids: list[int] = [
        SensorTypeEnum.METER_ACTIVE_POWER,
        SensorTypeEnum.MET_STATION_POA,
        SensorTypeEnum.PV_INVERTER_AC_POWER,
    ]

    project_schema = utils.get_project_schema(project_db=project_db)
    tags = await project_tags.get_project_tags_v2(
        sensor_type_ids=sensor_type_ids,
        deep=True,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    category_mapping: dict[int, str] = {
        SensorTypeEnum.METER_ACTIVE_POWER: "meter_power",
        SensorTypeEnum.MET_STATION_POA: "met",
        SensorTypeEnum.PV_INVERTER_AC_POWER: "pcs",
    }

    tag_ids = tags["tag_id"].astype(int)
    tag_sensor_type_ids = tags["sensor_type_id"].fillna(-1).astype(int)
    device_name_long = normalize_pandas_nullable(
        content=tags["device_name_long"].tolist()
    )
    tag_id_to_device_name_long = dict(zip(tag_ids, device_name_long, strict=True))
    tag_id_to_category = dict(
        zip(tag_ids, tag_sensor_type_ids.map(category_mapping), strict=True)
    )
    tag_id_to_device_id = dict(zip(tag_ids, tags["device_id"].astype(int), strict=True))

    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=tag_ids.tolist(),
        query_start=start,
        query_end=end,
        project_db=project_db,
        max_lookback_period=TimeOffset.FIVE_MINUTES,
    ).get()

    df = data_timeseries_instance.df.to_pandas()
    df = df.set_index("time")
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
    df.columns = df.columns.astype(int)

    data_meter_power = _get_sorted_horizontal_device_data(
        df=df,
        category="meter_power",
        tag_id_to_category=tag_id_to_category,
        tag_id_to_device_name_long=tag_id_to_device_name_long,
        tag_id_to_device_id=tag_id_to_device_id,
    )
    data_met = _get_sorted_horizontal_device_data(
        df=df,
        category="met",
        tag_id_to_category=tag_id_to_category,
        tag_id_to_device_name_long=tag_id_to_device_name_long,
        tag_id_to_device_id=tag_id_to_device_id,
    )
    data_pcs = _get_sorted_horizontal_device_data(
        df=df,
        category="pcs",
        tag_id_to_category=tag_id_to_category,
        tag_id_to_device_name_long=tag_id_to_device_name_long,
        tag_id_to_device_id=tag_id_to_device_id,
    )

    return {
        "times": df.index.tolist(),
        "meter_power": data_meter_power,
        "met": data_met,
        "pcs": data_pcs,
    }


@router.get("/single/{device_id}")
async def get_single_by_device_id(
    device_id: int,
    start: Annotated[
        datetime.datetime, Depends(filter_start_datetime_to_data_access_start_time)
    ],
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    """todo

    Args:
        device_id: Description for device_id.
        start: Description for start.
        end: Description for end.
        project: Description for project.
        project_db: Description for project_db.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    tags = await project_tags.get_project_tags_v2(
        device_ids=[device_id],
        deep=True,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    # At the time of writing, the tags.sensor_type_id column is nullable.
    # This means there could be some tags that have a null sensor_type_id and
    # some tags that have a sensor_type_id of 0 (ghost). We want to remove
    # both.
    tags = tags[tags["sensor_type_id"].notna()]
    tags = tags[tags["sensor_type_id"] != 0]

    {
        tag_id: name
        for tag_id, name in zip(
            tags["tag_id"], tags["sensor_type_name_long"], strict=True
        )
    }
    tag_id_to_name_scada = dict(zip(tags["tag_id"], tags["name_scada"], strict=True))
    tag_id_to_sensor_type_unit = dict(
        zip(tags["tag_id"], tags["sensor_type_unit"], strict=True)
    )

    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=tags["tag_id"].astype(int).tolist(),
        query_start=start,
        query_end=end,
        project_db=project_db,
        max_lookback_period=TimeOffset.FIVE_MINUTES,
    ).get()

    df = data_timeseries_instance.df.to_pandas()
    df = df.set_index("time")
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
    df.columns = df.columns.astype(int)

    return {
        "time": df.index.tolist(),
        "data": [
            {
                "name": tag_id_to_name_scada[c],
                "values": df[c].tolist(),
                "unit": tag_id_to_sensor_type_unit[c],
            }
            for c in df.columns.astype(int)
        ],
    }


@router.get(
    "/vertical/controller/{device_id}",
)
async def get_vertical_controller(
    device_id: int,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    # Manually define the device type IDs that are supported for each
    # technology (e.g. PV or BESS).
    # If the user selects a device that is not of a supported type, they will
    # get an error letting them know.
    """todo

    Args:
        device_id: Description for device_id.
        db: Description for db.
        project_db: Description for project_db.
        project: Description for project.
    """
    SUPPORTED_DEVICE_TYPE_IDS_BY_TECHNOLOGY: dict[Literal["pv", "bess"], list[int]] = {
        "pv": [
            DeviceTypeEnum.PV_INVERTER,
            DeviceTypeEnum.PV_INVERTER_MODULE,
            DeviceTypeEnum.PV_DC_COMBINER,
            DeviceTypeEnum.TRACKER_ROW,
        ],
        "bess": [
            DeviceTypeEnum.BESS_PCS,
            DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
            DeviceTypeEnum.BESS_PCS_MODULE,
            DeviceTypeEnum.BESS_DC_SKID,
            DeviceTypeEnum.BESS_BANK,
            DeviceTypeEnum.BESS_STRING,
        ],
    }

    # Get the device associated with the device_id
    project_schema = utils.get_project_schema(project_db=project_db)
    device = await project_devices.get_project_device(
        device_id=device_id,
        deep=False,
    ).get_async(output_type=OutputType.SQLALCHEMY, schema=project_schema)

    if device is None:
        raise HTTPException(
            status_code=404, detail="We are not able to find the device you requested."
        )

    # Once we have the device, determine the technology of the device from the
    # mapping above.
    for technology, _device_type_ids in SUPPORTED_DEVICE_TYPE_IDS_BY_TECHNOLOGY.items():
        if device.device_type_id in _device_type_ids:
            device_technology: Literal["pv", "bess"] = technology
            break
    # If the device is not of a supported type, we will raise an error.
    else:
        raise HTTPException(
            status_code=404,
            detail="The type of device that you have selected is not supported yet.",
        )

    # Determine the block device type ID based on the technology.
    # The block device is the greatest common ancestor of the returned devices.
    if device_technology == "pv":
        block_device_type_id = DeviceTypeEnum.PV_BLOCK
    else:
        block_device_type_id = DeviceTypeEnum.BESS_BLOCK

    # Get the block associated with the device_id
    block_df = await project_devices.get_project_devices(
        device_type_ids=[block_device_type_id],
        device_id_path_ancestor_of=device.device_id_path,
        deep=False,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if len(block_df) == 1:
        block = block_df.to_dict("records")[0]
    else:
        raise HTTPException(
            status_code=404,
            detail="Unable to find the block associated with the device you selected.",
        )

    # Get the device types that are supported for the device technology
    device_type_ids: list[int] = SUPPORTED_DEVICE_TYPE_IDS_BY_TECHNOLOGY[
        device_technology
    ]

    # Add additional requirements for including devices
    # NOTE - This is wrapped in a try/except block because accessing
    # project.spec is a bit volatile right now.
    # If the return statement of the get_project dependency is changed, there
    # is a possibility this will break.
    # (At the time of writing, we are manually parsing the returned db model
    # using Pydantic)
    try:
        spec_used_sensor_type_ids = (
            project.spec.used_sensor_type_ids  # type: ignore[attr-defined]
        )
        if spec_used_sensor_type_ids is not None:
            # If we do not have PV Inverter Module Power tags, remove the PV Inverter
            # Module device type
            if 3 not in spec_used_sensor_type_ids and 3 in device_type_ids:
                device_type_ids.remove(3)
    except Exception as e:
        logging.error(f"Error getting project spec: {e}")

    device_types_df = await crud_get_device_types(
        device_type_ids=device_type_ids,
    ).get_async(output_type=OutputType.POLARS)
    device_type_id_to_name_long: dict[int, str] = (
        dict(
            zip(
                device_types_df["device_type_id"].to_list(),
                device_types_df["name_long"].to_list(),
                strict=True,
            )
        )
        if not device_types_df.is_empty()
        else {}
    )

    # Get the child devices associated with the block
    child_devices_df = await project_devices.get_project_devices(
        device_type_ids=device_type_ids,
        device_id_descendent_of=int(block["device_id"]),
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    child_devices_df = child_devices_df.copy()
    child_devices_df["device_type_id"] = child_devices_df["device_type_id"].astype(int)
    child_devices_df["device_id"] = child_devices_df["device_id"].astype(int)

    # Define the type of the data that we will return
    class DeviceTreeItem(TypedDict):
        """todo"""

        id: int  # The device type ID
        label: str  # The device type name
        device_ids: list[int]  # The device IDs of the devices of this type
        initially_requested: (
            bool  # Whether the device was initially requested by the user
        )

    return_data: list[DeviceTreeItem] = []

    # Parse out child devices by device_type
    for device_type_id in device_type_ids:
        child_devices_of_type = child_devices_df[
            child_devices_df["device_type_id"] == device_type_id
        ]
        # If there are any child devices of this type, add them to the return data
        # NOTE, not all projects will have all the device types
        if len(child_devices_of_type) > 0:
            child_device_ids = child_devices_of_type["device_id"].tolist()
            return_data.append(
                {
                    "id": device_type_id,
                    "label": device_type_id_to_name_long[device_type_id],
                    "device_ids": child_device_ids,
                    "initially_requested": device_id in child_device_ids,
                }
            )

    return {
        "device_technology": device_technology,
        "device_tree": return_data,
    }


@router.get("/vertical")
async def get_vertical(
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    device_ids: Annotated[list[int], Query()],
    start: Annotated[
        datetime.datetime, Depends(filter_start_datetime_to_data_access_start_time)
    ],
    end: datetime.datetime,
):
    # Manually define the sensor type IDs that we want to fetch
    """todo

    Args:
        project: Description for project.
        project_db: Description for project_db.
        device_ids: Description for device_ids.
        start: Description for start.
        end: Description for end.
    """
    SENSOR_TYPE_IDS_TO_LABEL: dict[int, str] = {
        SensorTypeEnum.PV_INVERTER_AC_POWER: "Power (MW)",
        SensorTypeEnum.PV_INVERTER_MODULE_AC_POWER: "Power (MW)",
        SensorTypeEnum.PV_DC_COMBINER_CURRENT: "Current (A)",
        SensorTypeEnum.TRACKER_ROW_POSITION: "Position (deg)",
        SensorTypeEnum.BESS_PCS_AC_POWER: "Power (MW)",
        SensorTypeEnum.BESS_PCS_MODULE_GROUP_AC_POWER: "Power (MW)",
        SensorTypeEnum.BESS_PCS_MODULE_AC_POWER: "Power (MW)",
        SensorTypeEnum.BESS_ENCLOSURE_SOC_PERCENT: "SOC",
        SensorTypeEnum.BESS_DC_SKID_SOC_PERCENT: "SOC",
        SensorTypeEnum.BESS_BANK_SOC_PERCENT: "SOC",
        SensorTypeEnum.BESS_STRING_SOC_PERCENT: "SOC",  # bess_string_soc
    }

    # Get the tags associated with the device IDs and sensor type IDs
    project_schema = utils.get_project_schema(project_db=project_db)
    tags = await project_tags.get_project_tags_v2(
        device_ids=device_ids,
        sensor_type_ids=list(SENSOR_TYPE_IDS_TO_LABEL.keys()),
        deep=True,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    tag_id_to_device_name_long: dict[int, str] = dict(
        zip(tags["tag_id"], tags["device_name_long"], strict=True)
    )
    tag_id_to_device_id: dict[int, int] = dict(
        zip(tags["tag_id"], tags["device_id"].astype(int), strict=True)
    )
    tag_id_to_sensor_type_id: dict[int, int] = dict(
        zip(tags["tag_id"], tags["sensor_type_id"].fillna(0).astype(int), strict=True)
    )

    if tags.empty:
        raise HTTPException(
            status_code=404,
            detail=(
                "There are no tags associated with these devices that are "
                "required for this view."
            ),
        )

    # Get the data for the desired tags
    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=tags["tag_id"].astype(int).tolist(),
        query_start=start,
        query_end=end,
        project_db=project_db,
    ).get()

    df = data_timeseries_instance.df.to_pandas()
    df = df.set_index("time")
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
    df.columns = df.columns.astype(int)
    data = _get_sorted_vertical_device_data(
        df=df,
        tag_id_to_device_name_long=tag_id_to_device_name_long,
        tag_id_to_device_id=tag_id_to_device_id,
    )

    return {
        "times": df.index.tolist(),
        "data": data,
        "layout": {
            "y_axis_label": SENSOR_TYPE_IDS_TO_LABEL[
                tag_id_to_sensor_type_id[int(df.columns[0])]
            ],
        },
    }


@router.get("/data-availability")
async def get_data_availability(
    device_type_ids: Annotated[list[int], Query()],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    include_ghost_tags: Annotated[bool, Query()] = False,
):
    """Calculate data availability and staleness for a given set of device types.

    Args:
        device_type_ids: Device type ids to filter by.
        project_db: Project database session.
        include_ghost_tags: Include tags without sensor_type_id when True.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    df = await project_data_timeseries_last.get_data_timeseries_last(
        device_type_ids=device_type_ids,
        deep=True,
        include_ghost_tags=include_ghost_tags,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if df.empty:
        return []

    df = df[
        [
            "tag_id",
            "time",
            "sensor_type_id",
            "device_id",
            "device_type_id",
            "device_name",
        ]
    ]
    df["age"] = (
        pd.Timestamp.now(tz="UTC") - pd.to_datetime(df["time"], utc=True)
    ).dt.total_seconds()

    max_ages = df.groupby("sensor_type_id")["age"].median() * 2
    max_ages = max_ages.apply(lambda x: max(x, 3600))
    df["max_age"] = df["sensor_type_id"].map(max_ages)
    df["max_age"] = df["max_age"].fillna(3600)
    df["stale"] = df["age"] > df["max_age"]
    df["age_pct"] = df["age"] / df["max_age"]
    df = df[df["sensor_type_id"] > 0]
    df = df.replace({np.nan: None})

    return df.to_dict(orient="records")


@router.get("/data-availability-v2")
async def get_data_availability_v2(
    device_type_ids: Annotated[list[int], Query()],
    project_name_short: Annotated[
        str,
        Depends(dependencies.get_project_name_short),
    ],
    include_ghost_tags: Annotated[bool, Query()] = False,
):
    """Calculates data availability and staleness for a given set of device types.
        This implementation uses a Common Table Expression (CTE) and the PostgreSQL
        ANY() operator to efficiently handle a large number of device_type_ids,
        avoiding the 32,767 parameter limit.

    Args:
        device_type_ids: Description for device_type_ids.
        project_name_short: Description for project_name_short.
        include_ghost_tags: Description for include_ghost_tags.
    """

    query = project_data_timeseries_last.get_data_timeseries_last_v2(
        device_type_ids=device_type_ids,
        include_ghost_tags=include_ghost_tags,
    )
    df = await query.get_async(schema=project_name_short)

    if df.is_empty():
        return []

    # Detect stale
    df = df.with_columns(
        max_age=(pl.col("median_age") * 2).clip(lower_bound=3600).fill_null(3600),
    ).with_columns(
        stale=(pl.col("age") > pl.col("max_age")),
        age_pct=(pl.col("age") / pl.col("max_age")),
    )

    # 6. Filter and select the final columns for the response.
    df = df.filter(pl.col("sensor_type_id") > 0).select(
        [
            "tag_id",
            "time",
            "sensor_type_id",
            "device_id",
            "device_type_id",
            "device_name",
            "age",
            "max_age",
            "stale",
            "age_pct",
        ]
    )

    return polars_to_arrow_response(df=df, filename="data_availability.arrow")
