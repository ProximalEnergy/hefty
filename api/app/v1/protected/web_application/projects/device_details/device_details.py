import datetime
import logging
from typing import Annotated, Literal, TypedDict

import numpy as np
import pandas as pd
import polars as pl
from core.crud.operational.device_types import get_device_types as crud_get_device_types
from core.db_query import OutputType
from core.enumerations import DeviceType
from core.enumerations import SensorType as SensorTypeEnum
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse
from natsort import natsorted
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from app._utils.arrow import polars_to_arrow_response
from core import models

router = APIRouter(
    prefix="/device-details",
    tags=["device-details"],
    include_in_schema=utils.get_include_in_schema(),
)


@router.get(
    "/horizontal/bess",
    response_class=ORJSONResponse,
)
def get_horizontal_bess(
    start: datetime.datetime,
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    # Determine what is the "highest" level of battery storage data
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        project_db: TODO: describe.
    """
    used_sensor_type_ids = project.spec.used_sensor_type_ids  # type: ignore
    if SensorTypeEnum.BESS_ENCLOSURE_SOC_PERCENT in used_sensor_type_ids:
        bess_sensor_type_id = SensorTypeEnum.BESS_ENCLOSURE_SOC_PERCENT
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

    tags = core.crud.project.tags.get_project_tags(
        db=project_db,
        sensor_type_ids=sensor_type_ids,
        deep=True,
    ).models()

    category_mapping: dict[int, str] = {
        SensorTypeEnum.BESS_PCS_AC_POWER: "pcs",
        SensorTypeEnum.PROJECT_SOC_PERCENT: "meter_soc",
        SensorTypeEnum.METER_ACTIVE_POWER: "meter_power",
        SensorTypeEnum.BESS_ENCLOSURE_SOC_PERCENT: "battery",
        SensorTypeEnum.BESS_BANK_SOC_PERCENT: "battery",
        SensorTypeEnum.BESS_STRING_SOC_PERCENT: "battery",
    }

    tag_id_to_device_name_long = {t.tag_id: t.device.name_long for t in tags}
    tag_id_to_category = {
        t.tag_id: category_mapping.get(t.sensor_type_id or -1) for t in tags
    }
    tag_id_to_device_id = {t.tag_id: t.device_id for t in tags}

    df = utils.data_df(
        project_db=project_db,
        project=project,
        tags=tags,
        start=start,
        end=end,
        get_last=True,
        fillna_zero=False,
    )
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)

    def _get_data(*, category: str):
        """todo

        Args:
            category: TODO: describe.
        """
        data = [
            {
                "values": df[c].tolist(),
                "name": tag_id_to_device_name_long[c],
                "device_id": tag_id_to_device_id[c],
            }
            for c in df.columns.astype(int)
            if tag_id_to_category[c] == category
        ]

        data = natsorted(data, key=lambda x: x["name"])

        return data

    data_meter_power = _get_data(category="meter_power")
    data_meter_soc = _get_data(category="meter_soc")
    data_pcs = _get_data(category="pcs")
    data_battery = _get_data(category="battery")

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
    response_class=ORJSONResponse,
    response_model=DeviceDetailsHorizontalPV,
)
def get_horizontal_pv(
    start: datetime.datetime,
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        project_db: TODO: describe.
    """
    sensor_type_ids: list[int] = [
        SensorTypeEnum.METER_ACTIVE_POWER,
        SensorTypeEnum.MET_STATION_POA,
        SensorTypeEnum.PV_PCS_AC_POWER,
    ]

    tags = core.crud.project.tags.get_project_tags(
        db=project_db,
        sensor_type_ids=sensor_type_ids,
        deep=True,
    ).models()

    category_mapping: dict[int, str] = {
        SensorTypeEnum.METER_ACTIVE_POWER: "meter_power",
        SensorTypeEnum.MET_STATION_POA: "met",
        SensorTypeEnum.PV_PCS_AC_POWER: "pcs",
    }

    tag_id_to_device_name_long = {t.tag_id: t.device.name_long for t in tags}
    tag_id_to_category = {
        t.tag_id: category_mapping.get(t.sensor_type_id or -1) for t in tags
    }
    tag_id_to_device_id = {t.tag_id: t.device_id for t in tags}

    df = utils.data_df(
        project_db=project_db,
        project=project,
        tags=tags,
        start=start,
        end=end,
        get_last=True,
        fillna_zero=False,
    )
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)

    def _get_data(*, category: str):
        """todo

        Args:
            category: TODO: describe.
        """
        data = [
            {
                "values": df[c].tolist(),
                "name": tag_id_to_device_name_long[c],
                "device_id": tag_id_to_device_id[c],
            }
            for c in df.columns.astype(int)
            if tag_id_to_category[c] == category
        ]

        data = natsorted(data, key=lambda x: x["name"])

        return data

    data_meter_power = _get_data(category="meter_power")
    data_met = _get_data(category="met")
    data_pcs = _get_data(category="pcs")

    return {
        "times": df.index.tolist(),
        "meter_power": data_meter_power,
        "met": data_met,
        "pcs": data_pcs,
    }


@router.get(
    "/single/{device_id}",
    response_class=ORJSONResponse,
)
def get_single_by_device_id(
    device_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    """todo

    Args:
        device_id: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        project_db: TODO: describe.
    """
    tags = core.crud.project.tags.get_project_tags(
        db=project_db,
        device_ids=[device_id],
        deep=True,
    ).models()
    # At the time of writing, the tags.sensor_type_id column is nullable.
    # This means there could be some tags that have a null sensor_type_id and
    # some tags that have a sensor_type_id of 0 (ghost). We want to remove
    # both.
    tags = [t for t in tags if t.sensor_type_id not in [0, None]]

    {t.tag_id: t.sensor_type.name_long for t in tags}
    tag_id_to_name_scada = {t.tag_id: t.name_scada for t in tags}
    tag_id_to_sensor_type_unit = {t.tag_id: t.sensor_type.unit for t in tags}

    df = utils.data_df(
        project_db=project_db,
        project=project,
        tags=tags,
        start=start,
        end=end,
        get_last=True,
        fillna_zero=False,
    )
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)

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
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    # Manually define the device type IDs that are supported for each
    # technology (e.g. PV or BESS).
    # If the user selects a device that is not of a supported type, they will
    # get an error letting them know.
    """todo

    Args:
        device_id: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
    """
    SUPPORTED_DEVICE_TYPE_IDS_BY_TECHNOLOGY: dict[Literal["pv", "bess"], list[int]] = {
        "pv": [
            2,  # "PV PCS",
            3,  # "PV PCS Module",
            9,  # "PV DC Combiner",
            29,  # "Tracker Row",
        ],
        "bess": [
            13,  # "BESS PCS",
            32,  # "BESS PCS Module Group",
            33,  # "BESS PCS Module",
            26,  # "BESS Bank",
            27,  # "BESS String",
        ],
    }

    # Get the device associated with the device_id
    project_schema = utils.get_project_schema(project_db=project_db)
    device = await core.crud.project.devices.get_project_device(
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
        block_device_type_id = DeviceType.BLOCK
    else:
        block_device_type_id = DeviceType.BESS_BLOCK

    # Get the block associated with the device_id
    block_df = await core.crud.project.devices.get_project_devices(
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
        spec_used_sensor_type_ids = project.spec.used_sensor_type_ids  # type: ignore[attr-defined]
        if spec_used_sensor_type_ids is not None:
            # If we do not have PV PCS Module Power tags, remove the PV PCS
            # Module device type
            if 3 not in spec_used_sensor_type_ids and 3 in device_type_ids:
                device_type_ids.remove(3)
    except Exception as e:
        logging.error(f"Error getting project spec: {e}")

    device_types: list[models.DeviceType] = await crud_get_device_types(
        db=db,
        device_type_ids=device_type_ids,
    )
    device_type_id_to_name_long: dict[int, str] = {
        dt.device_type_id: dt.name_long for dt in device_types
    }

    # Get the child devices associated with the block
    child_devices_df = await core.crud.project.devices.get_project_devices(
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


@router.get(
    "/vertical",
    response_class=ORJSONResponse,
)
def get_vertical(
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    device_ids: Annotated[list[int], Query()],
    start: datetime.datetime,
    end: datetime.datetime,
):
    # Manually define the sensor type IDs that we want to fetch
    """todo

    Args:
        project: TODO: describe.
        project_db: TODO: describe.
        device_ids: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    SENSOR_TYPE_IDS_TO_LABEL: dict[int, str] = {
        2: "Power (MW)",  # pv_pcs_ac_power
        3: "Power (MW)",  # pv_pcs_ac_power_module
        27: "Current (A)",  # pv_dc_combiner_current
        24: "Position (deg)",  # tracker_row_position
        31: "Power (MW)",  # bess_pcs_ac_power
        121: "Power (MW)",  # bess_pcs_module_group_ac_power
        106: "Power (MW)",  # bess_pcs_module_ac_power
        43: "SOC",  # bess_dc_enclosure_soc
        44: "SOC",  # bess_bank_soc
        45: "SOC",  # bess_string_soc
    }

    # Get the tags associated with the device IDs and sensor type IDs
    tags: list[models.Tag] = core.crud.project.tags.get_project_tags(
        db=project_db,
        device_ids=device_ids,
        sensor_type_ids=list(SENSOR_TYPE_IDS_TO_LABEL.keys()),
        deep=True,
    ).models()
    tag_id_to_device_name_long: dict[int, str] = {
        t.tag_id: t.device.name_long for t in tags
    }
    tag_id_to_device_id: dict[int, int] = {t.tag_id: t.device_id for t in tags}
    tag_id_to_sensor_type_id: dict[int, int] = {
        t.tag_id: t.sensor_type_id or 0 for t in tags
    }

    if len(tags) == 0:
        raise HTTPException(
            status_code=404,
            detail=(
                "There are no tags associated with these devices that are "
                "required for this view."
            ),
        )

    # Get the data for the desired tags
    df: pd.DataFrame = utils.data_df(
        project_db=project_db,
        project=project,
        tags=tags,
        start=start,
        end=end,
    )
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)

    return {
        "times": df.index.tolist(),
        "data": [
            {
                "name": tag_id_to_device_name_long[int(c)],
                "values": df[c].tolist(),
                "device_id": tag_id_to_device_id[int(c)],
            }
            for c in df.columns
        ],
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
    df = await core.crud.project.data_timeseries_last.get_data_timeseries_last(
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
        device_type_ids: TODO: describe.
        project_name_short: TODO: describe.
        include_ghost_tags: TODO: describe.
    """

    query = core.crud.project.data_timeseries_last.get_data_timeseries_last_v2(
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
