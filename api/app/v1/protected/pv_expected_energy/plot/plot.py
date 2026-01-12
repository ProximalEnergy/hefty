import datetime
from typing import Annotated

import pandas as pd
from app import dependencies, interfaces, utils
from app._utils.recursive_parents import get_recursive_parents
from app.utils import data_df
from core.crud.operational.device_types import get_device_types
from core.db_query import OutputType
from core.enumerations import DeviceType, SensorType
from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from core import models

router = APIRouter(prefix="/plot")


class UtilityExpectedResponse(BaseModel):
    """todo"""

    parent_devices: list[interfaces.Device]
    times: list[datetime.datetime]
    actual: dict[str, list[float]]
    expected_clean: dict[str, list[float | str | datetime.datetime | None]]
    expected_soiled: dict[str, list[float | str | datetime.datetime | None]]
    poa: dict[str, list[float | None]]
    soiling: dict[str, list[float | None]]


@router.get(
    "",
    response_model=UtilityExpectedResponse,
    response_class=ORJSONResponse,
)
async def utility_expected(
    device_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
    warranted_degradation: Annotated[bool, Query()] = False,
    db: AsyncSession = Depends(dependencies.get_async_db),
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project_api),
):
    """This function facilitates all backend data required for the Superadmin
    Utility Expected Plotting page. Data returned includes parent device tree
    up to root, expected power data, and actual power data. This data is visible
    exclusively to Proximal Superadmins, and as such can be changed more freely
    to fit the use case of the page.

    Args:
        device_id: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        warranted_degradation: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
    """
    # Get parentage up to root using recursive parents crud function
    parent_devices = get_recursive_parents(db=project_db, device_id=device_id)

    # Add device name full to all devices
    device_types = await get_device_types(
        db=db,
        device_type_ids=[x.device_type_id for x in parent_devices],
    )
    device_type_id_to_name_long = {
        device_type.device_type_id: device_type.name_long
        for device_type in device_types
    }
    for device in parent_devices:
        if not device.name_long:
            device.name_long = ""
    device_id_to_device_name_full = {
        device.device_id: device_type_id_to_name_long[device.device_type_id]
        + " "
        + (device.name_long or "")
        for device in parent_devices
    }

    parent_devices = [
        {
            **device.__dict__,
            "name_full": device_id_to_device_name_full.get(device.device_id, ""),
        }
        for device in parent_devices
    ]

    project_schema = utils.get_project_schema(project_db=project_db)
    device_df = await core.crud.project.devices.get_project_device(
        device_id=device_id,
        deep=False,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    if device_df.empty:
        raise HTTPException(status_code=404, detail="Device not found")
    device = device_df.to_dict("records")[0]

    # Meter
    if device["device_type_id"] == DeviceType.METER:
        sensor_type_ids = [SensorType.METER_ACTIVE_POWER]
        expected_metric_id_clean = 11 if not warranted_degradation else 5
        expected_metric_id_soiled = 12 if not warranted_degradation else 6
        multiplier = 1_000.0
        expected_device_ids = [1]
        pv_dc_combiner = False
    # PV PCS
    elif device["device_type_id"] == DeviceType.PV_PCS:
        sensor_type_ids = [SensorType.PV_PCS_AC_POWER]
        expected_metric_id_clean = 9 if not warranted_degradation else 3
        expected_metric_id_soiled = 10 if not warranted_degradation else 4
        multiplier = 1_000.0
        expected_device_ids = [device_id]
        pv_dc_combiner = False
    # PV DC Combiner
    elif device["device_type_id"] == DeviceType.PV_DC_COMBINER:
        sensor_type_ids = [SensorType.PV_DC_COMBINER_CURRENT]
        expected_metric_id_clean = 7 if not warranted_degradation else 1
        expected_metric_id_soiled = 8 if not warranted_degradation else 2
        multiplier = 1 / 1_000
        expected_device_ids = [device_id]
        pv_dc_combiner = True
    else:
        raise HTTPException(status_code=422, detail="Invalid device type")

    # Query device data
    # If combiner, need to pull PCS module voltage and combiner current
    if pv_dc_combiner:
        device_pv_pcs_df = await core.crud.project.devices.get_project_devices(
            device_type_ids=[DeviceType.PV_PCS],
            device_id_path_ancestor_of=device["device_id_path"],
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        if device_pv_pcs_df.empty:
            raise HTTPException(status_code=404, detail="PV PCS device not found")
        device_pv_pcs = device_pv_pcs_df.to_dict("records")[0]

        devices_pv_pcs_modules_df = await core.crud.project.devices.get_project_devices(
            device_type_ids=[DeviceType.PV_PCS_MODULE],
            device_id_descendent_of=int(device_pv_pcs["device_id"]),
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

        device_ids_pv_pcs_modules = (
            devices_pv_pcs_modules_df["device_id"].astype(int).tolist()
        )

        tags_pv_pcs_module_voltage = core.crud.project.tags.get_project_tags(
            project_db,
            device_ids=device_ids_pv_pcs_modules,
            sensor_type_ids=[SensorType.PV_PCS_MODULE_DC_VOLTAGE],
        ).models()

        ## Kind of a hacky workaround:
        ## If there are no tags for PV PCS Module Voltage,
        ## try using PV PCS DC Voltage instead.
        if len(tags_pv_pcs_module_voltage) == 0:
            tags_pv_pcs_module_voltage = core.crud.project.tags.get_project_tags(
                project_db,
                device_ids=[int(device_pv_pcs["device_id"])],
                sensor_type_ids=[SensorType.PV_PCS_DC_VOLTAGE],
            ).models()

        tags_pv_dc_combiner_current = core.crud.project.tags.get_project_tags(
            project_db,
            device_ids=[device_id],
            sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT],
        ).models()

        df_pv_pcs_module_voltage = data_df(
            project_db,
            project,
            tags=tags_pv_pcs_module_voltage,
            start=start,
            end=end,
            fillna_zero=False,
        )

        df_pv_dc_combiner_current = data_df(
            project_db,
            project,
            tags=tags_pv_dc_combiner_current,
            start=start,
            end=end,
            fillna_zero=False,
        )

        s_actual = df_pv_pcs_module_voltage.mean(axis=1).mul(
            df_pv_dc_combiner_current.iloc[:, 0],
        )

    # For non-combiner devices, can pull power directly
    else:
        tags = core.crud.project.tags.get_project_tags(
            project_db,
            device_ids=[device_id],
            sensor_type_ids=sensor_type_ids,
        ).models()

        s_actual = data_df(
            project_db,
            project,
            tags=tags,
            start=start,
            end=end,
            fillna_zero=False,
        ).iloc[:, 0]

    # Convert to project timezone and ensure power is in kW
    s_actual.index = pd.to_datetime(s_actual.index).tz_convert(project.time_zone)
    s_actual = s_actual * multiplier

    # Query expected data
    data_expected = core.crud.project.data_expected.get_project_data_expected(
        project_db,
        start=start,
        end=end,
        device_ids=expected_device_ids,
    ).models()

    if len(data_expected) == 0:
        raise HTTPException(status_code=422, detail="No expected data found")

    df_expected = pd.DataFrame([d.__dict__ for d in data_expected]).drop(
        columns=["_sa_instance_state", "device_id"],
    )

    def parse_df(*, expected_metric_id: int):
        """todo

        Args:
            expected_metric_id: TODO: describe.
        """
        df = df_expected[df_expected["expected_metric_id"] == expected_metric_id]
        df = df.set_index("time")
        df = df.reindex(s_actual.index)
        df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
        df["value"] = df["value"] / 1_000  # Convert from W to kW

        return df

    df_expected_clean = parse_df(expected_metric_id=expected_metric_id_clean)
    df_expected_soiled = parse_df(expected_metric_id=expected_metric_id_soiled)

    df_poa = data_df(
        project_db,
        project,
        tags=core.crud.project.tags.get_project_tags(
            project_db,
            sensor_type_ids=[SensorType.MET_STATION_POA],
        ).models(),
        start=start,
        end=end,
        fillna_zero=False,
    )

    try:
        df_soiling = data_df(
            project_db,
            project,
            tags=core.crud.project.tags.get_project_tags(
                project_db,
                sensor_type_ids=[SensorType.MET_STATION_SOIL_PERCENT],
            ).models(),
            start=start,
            end=end,
            fillna_zero=False,
        )
    except HTTPException:
        df_soiling = pd.DataFrame(index=s_actual.index)

    out = {}

    out["parent_devices"] = parent_devices

    out["times"] = s_actual.index.tolist()

    out["actual"] = {"power": s_actual.fillna(0).tolist()}  # type: ignore

    out["expected_clean"] = {  # type: ignore
        "power": df_expected_clean["value"].tolist(),
        "version": df_expected_clean["version"].astype(str).fillna("").tolist(),
        "unique_versions": sorted(
            [str(v) for v in df_expected_clean["version"].dropna().unique().tolist()],
        ),
        "difference": (df_expected_clean["value"] - s_actual).fillna(0).tolist(),
    }

    out["expected_soiled"] = {  # type: ignore
        "power": df_expected_soiled["value"].tolist(),
        "version": df_expected_soiled["version"].astype(str).fillna("").tolist(),
        "unique_versions": sorted(
            [str(v) for v in df_expected_soiled["version"].dropna().unique().tolist()],
        ),
        "difference": (df_expected_soiled["value"] - s_actual).fillna(0).tolist(),
    }

    out["poa"] = {str(col): df_poa[col].tolist() for col in df_poa.columns}  # type: ignore

    out["soiling"] = {str(col): df_soiling[col].tolist() for col in df_soiling.columns}  # type: ignore

    return out
