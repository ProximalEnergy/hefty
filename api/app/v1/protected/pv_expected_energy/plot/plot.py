import datetime
from typing import Annotated

import pandas as pd
from app import dependencies, interfaces, utils
from app._utils.recursive_parents import get_recursive_parents
from core.crud.operational.device_types import get_device_types
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import DeviceType, SensorType
from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException
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
        device_id: Description for device_id.
        start: Description for start.
        end: Description for end.
        warranted_degradation: Description for warranted_degradation.
        db: Description for db.
        project_db: Description for project_db.
        project: Description for project.
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
    elif device["device_type_id"] == DeviceType.PV_INVERTER:
        sensor_type_ids = [SensorType.PV_INVERTER_AC_POWER]
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
        device_pv_inverter_df = await core.crud.project.devices.get_project_devices(
            device_type_ids=[DeviceType.PV_INVERTER],
            device_id_path_ancestor_of=device["device_id_path"],
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        if device_pv_inverter_df.empty:
            raise HTTPException(status_code=404, detail="PV PCS device not found")
        device_pv_inverter = device_pv_inverter_df.to_dict("records")[0]

        devices_pv_inverter_modules_df = (
            await core.crud.project.devices.get_project_devices(
                device_type_ids=[DeviceType.PV_INVERTER_MODULE],
                device_id_descendent_of=int(device_pv_inverter["device_id"]),
            ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        )

        device_ids_pv_inverter_modules = (
            devices_pv_inverter_modules_df["device_id"].astype(int).tolist()
        )

        tags_pv_inverter_module_voltage = (
            await core.crud.project.tags.get_project_tags_v2(
                device_ids=device_ids_pv_inverter_modules,
                sensor_type_ids=[SensorType.PV_INVERTER_MODULE_DC_VOLTAGE],
            ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        )

        ## Kind of a hacky workaround:
        ## If there are no tags for PV PCS Module Voltage,
        ## try using PV PCS DC Voltage instead.
        if tags_pv_inverter_module_voltage.empty:
            tags_pv_inverter_module_voltage = (
                await core.crud.project.tags.get_project_tags_v2(
                    device_ids=[int(device_pv_inverter["device_id"])],
                    sensor_type_ids=[SensorType.PV_INVERTER_DC_VOLTAGE],
                ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
            )

        tags_pv_dc_combiner_current = await core.crud.project.tags.get_project_tags_v2(
            device_ids=[device_id],
            sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT],
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

        data_timeseries_instance = await DataTimeseries(
            project_name_short=project.name_short,
            filter_method=FilterMethod.TAG_IDS,
            filter_values=tags_pv_inverter_module_voltage["tag_id"]
            .astype(int)
            .tolist(),
            query_start=start,
            query_end=end,
            project_db=project_db,
        ).get()

        df_pv_inverter_module_voltage = data_timeseries_instance.df.to_pandas()
        df_pv_inverter_module_voltage = df_pv_inverter_module_voltage.set_index("time")
        df_pv_inverter_module_voltage.index = pd.to_datetime(
            df_pv_inverter_module_voltage.index
        ).tz_convert(project.time_zone)
        df_pv_inverter_module_voltage.columns = (
            df_pv_inverter_module_voltage.columns.astype(int)
        )

        data_timeseries_instance = await DataTimeseries(
            project_name_short=project.name_short,
            filter_method=FilterMethod.TAG_IDS,
            filter_values=tags_pv_dc_combiner_current["tag_id"].astype(int).tolist(),
            query_start=start,
            query_end=end,
            project_db=project_db,
        ).get()

        df_pv_dc_combiner_current = data_timeseries_instance.df.to_pandas()
        df_pv_dc_combiner_current = df_pv_dc_combiner_current.set_index("time")
        df_pv_dc_combiner_current.index = pd.to_datetime(
            df_pv_dc_combiner_current.index
        ).tz_convert(project.time_zone)
        df_pv_dc_combiner_current.columns = df_pv_dc_combiner_current.columns.astype(
            int
        )

        s_actual = df_pv_inverter_module_voltage.mean(axis=1).mul(
            df_pv_dc_combiner_current.iloc[:, 0],
        )

    # For non-combiner devices, can pull power directly
    else:
        tags = await core.crud.project.tags.get_project_tags_v2(
            device_ids=[device_id],
            sensor_type_ids=sensor_type_ids,
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

        data_timeseries_instance = await DataTimeseries(
            project_name_short=project.name_short,
            filter_method=FilterMethod.TAG_IDS,
            filter_values=tags["tag_id"].astype(int).tolist(),
            query_start=start,
            query_end=end,
            project_db=project_db,
        ).get()

        df_actual = data_timeseries_instance.df.to_pandas()
        df_actual = df_actual.set_index("time")
        df_actual.index = pd.to_datetime(df_actual.index).tz_convert(project.time_zone)
        df_actual.columns = df_actual.columns.astype(int)

        s_actual = df_actual.iloc[:, 0]

    # Convert to project timezone and ensure power is in kW
    s_actual.index = pd.to_datetime(s_actual.index).tz_convert(project.time_zone)
    s_actual = s_actual * multiplier

    # Query expected data
    data_expected = await core.crud.project.data_expected.get_project_data_expected(
        start=start,
        end=end,
        device_ids=expected_device_ids,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if data_expected.empty:
        raise HTTPException(status_code=422, detail="No expected data found")

    df_expected = data_expected.copy().drop(columns=["device_id"])
    df_expected["time"] = pd.to_datetime(df_expected["time"], errors="coerce")
    if getattr(df_expected["time"].dt, "tz", None) is None:
        df_expected["time"] = df_expected["time"].dt.tz_localize(
            "UTC", nonexistent="NaT", ambiguous="NaT"
        )
    df_expected["time"] = df_expected["time"].dt.tz_convert(project.time_zone)

    def parse_df(*, expected_metric_id: int):
        """todo

        Args:
            expected_metric_id: Description for expected_metric_id.
        """
        df = df_expected[df_expected["expected_metric_id"] == expected_metric_id]
        df = df.set_index("time")
        df = df.reindex(s_actual.index)
        df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
        df["value"] = df["value"] / 1_000  # Convert from W to kW

        return df

    df_expected_clean = parse_df(expected_metric_id=expected_metric_id_clean)
    df_expected_soiled = parse_df(expected_metric_id=expected_metric_id_soiled)

    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.SENSOR_TYPE_IDS,
        filter_values=[SensorType.MET_STATION_POA],
        query_start=start,
        query_end=end,
        project_db=project_db,
    ).get()

    df_poa = data_timeseries_instance.df.to_pandas()
    df_poa = df_poa.set_index("time")
    df_poa.index = pd.to_datetime(df_poa.index).tz_convert(project.time_zone)
    df_poa.columns = df_poa.columns.astype(int)

    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.SENSOR_TYPE_IDS,
        filter_values=[SensorType.MET_STATION_SOIL_PERCENT],
        query_start=start,
        query_end=end,
        project_db=project_db,
    ).get()

    df_soiling = data_timeseries_instance.df.to_pandas()
    df_soiling = df_soiling.set_index("time")
    df_soiling.index = pd.to_datetime(df_soiling.index).tz_convert(project.time_zone)
    df_soiling.columns = df_soiling.columns.astype(int)

    if df_soiling.empty:
        df_soiling = pd.DataFrame(index=s_actual.index, columns=df_soiling.columns)

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
