import datetime
import typing
from typing import Annotated

import core.crud.project.data_expected
import core.crud.project.data_timeseries_last
import core.crud.project.devices
import pandas as pd
from core.crud.operational.sensor_types import get_sensor_types
from core.crud.project.data_timeseries_last import (
    get_data_timeseries_latest_by_device_type,
)
from core.db_query import OutputType
from core.enumerations import DeviceType, SensorType
from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse
from natsort import natsorted
from pydantic import BaseModel
from sqlalchemy import Float, cast, func, select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from app.dependencies import get_project_db
from app.logger import logger
from core import models

router = APIRouter(
    prefix="/real-time",
    tags=["real-time"],
    include_in_schema=utils.get_include_in_schema(),
)


def _extract_numeric_value_from_row(*, row) -> float | None:
    """Return the first non-NULL numeric column from a DataFrame row (named tuple)."""
    # todo: unit_offset is not applied in this function however it should probably be
    # applied in the get_data_timeseries_latest_by_device_type function instead
    for attr in (
        "value_integer",
        "value_bigint",
        "value_real",
        "value_double",
    ):
        value = getattr(row, attr)
        if value is not None and not pd.isna(value):
            value = float(value)
            if hasattr(row, "unit_scale") and row.unit_scale is not None:
                value = value * row.unit_scale
            return float(value)
    return None


# --- 2) optional: human names for each sensor_type_id you care about --------------
SENSOR_TYPE_NAME = {
    2: "AC Power",
    3: "AC Power",
    9: "AC Power Setpoint",
    24: "Tracker Position",
    25: "Tracker Setpoint",
    27: "Combiner Current",
    31: "AC Power",
    45: "SOC",
    82: "Voltage",
    106: "AC Power",
    121: "AC Power",
    130: "AC Power",
}


# --- 3) Expected power endpoint (must come before generic device_type_id route) ---
@router.get(
    "/{device_type_id}/expected-power",
    response_class=ORJSONResponse,
)
async def get_expected_power_by_device_type_id(
    device_type_id: int,
    project_db: Session = Depends(get_project_db),
    project: models.Project = Depends(dependencies.get_project_api),
):
    """Get latest expected power for all devices of a given device type.

    Uses the same logic as utility_expected in gis.py to fetch expected power
    with proper fallback handling for expected_metric_ids.

    Args:
        device_type_id: The device type ID to fetch expected power for.
        project_db: Database session.
        project: Project model.
    """
    # Get all devices of this type
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_df = await core.crud.project.devices.get_project_devices(
        device_type_ids=[device_type_id],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if devices_df.empty:
        return {"device_ids": [], "expected_power": {}}

    device_ids = devices_df["device_id"].astype(int).tolist()

    # Determine expected_metric_ids based on device type (same as utility_expected)
    if device_type_id == DeviceType.PV_PCS:
        expected_metric_ids_fallback = [10, 9, 4, 3]  # With soiling first, then without
        expected_device_ids_for_query = device_ids
    elif device_type_id == DeviceType.PV_DC_COMBINER:
        expected_metric_ids_fallback = [8, 7, 2, 1]
        expected_device_ids_for_query = device_ids
    else:
        # Unsupported device type
        return {"device_ids": device_ids, "expected_power": {}}

    # Get time range (last hour, same as utility_expected default)
    end = pd.Timestamp.utcnow().floor("5min")
    start = end - pd.Timedelta(hours=1)
    start_query = pd.Timestamp(start).tz_convert(project.time_zone)
    end_query = pd.Timestamp(end).tz_convert(project.time_zone)

    # Query Expected Data with Fallbacks (same logic as utility_expected)
    data_expected = None
    found_metric_id = None
    for expected_metric_id in expected_metric_ids_fallback:
        data_expected = await core.crud.project.data_expected.get_project_data_expected(
            start=start_query,
            end=end_query,
            device_ids=expected_device_ids_for_query,
            expected_metric_ids=[expected_metric_id],
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        if not data_expected.empty:
            found_metric_id = expected_metric_id
            break

    if data_expected is None or data_expected.empty:
        # No expected data found
        return {
            "device_ids": device_ids,
            "expected_power": {did: None for did in device_ids},
        }

    # Convert to DataFrame and get latest values
    df_expected_all = data_expected.copy()
    df_expected_all["time"] = pd.to_datetime(df_expected_all["time"], errors="coerce")
    if getattr(df_expected_all["time"].dt, "tz", None) is None:
        df_expected_all["time"] = df_expected_all["time"].dt.tz_localize(
            "UTC", nonexistent="NaT", ambiguous="NaT"
        )
    df_expected_all["time"] = df_expected_all["time"].dt.tz_convert(project.time_zone)
    df_expected_filtered = df_expected_all[
        df_expected_all["expected_metric_id"] == found_metric_id
    ]

    if df_expected_filtered.empty:
        return {
            "device_ids": device_ids,
            "expected_power": {did: None for did in device_ids},
        }

    # Pivot to get device_id columns
    df_expected_pivot = df_expected_filtered.pivot(
        index="time",
        columns="device_id",
        values="value",
    )

    # Convert from W to MW (divide by 1,000,000)
    df_expected_pivot = df_expected_pivot / 1_000_000

    # Get the latest value for each device
    expected_power_dict: dict[int, float | None] = {}
    for device_id in device_ids:
        if device_id in df_expected_pivot.columns:
            # Get the last non-null value
            series = df_expected_pivot[device_id].dropna()
            if not series.empty:
                expected_power_dict[device_id] = float(series.iloc[-1])
            else:
                expected_power_dict[device_id] = None
        else:
            expected_power_dict[device_id] = None

    return {
        "device_ids": device_ids,
        "expected_power": expected_power_dict,
    }


# --- 4) the main endpoint -----------------------------------------------
@router.get("/{device_type_id}", response_class=ORJSONResponse)
async def get_by_device_type_id(
    device_type_id: int,
    sensor_type_ids: Annotated[list[int] | None, Query()] = None,
    project_db: Session = Depends(get_project_db),
):
    # ── fetch latest values ─────────────────────────────────────────────────────
    """todo

    Args:
        device_type_id: TODO: describe.
        sensor_type_ids: TODO: describe.
        project_db: TODO: describe.
    """
    project_schema = utils.get_project_schema(project_db=project_db)

    data_df = await get_data_timeseries_latest_by_device_type(
        device_type_id=device_type_id,
        sensor_type_ids=sensor_type_ids,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if data_df.empty:
        return {  # empty stub so TS side stays happy
            "device_ids": [],
            "device_names": [],
            "device_names_x": [],
            "device_names_y": [],
            "traces": [],
        }

    # ── build *unique* device list in deterministic order ───────────────────────
    device_ids: list[int] = data_df["device_id"].unique().tolist()

    # ── device metadata (names) --------------------------------------------------
    devices_df = await core.crud.project.devices.get_project_devices(
        device_ids=device_ids,
        device_type_ids=[device_type_id],
        deep=False,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    devices_df = devices_df[devices_df["device_type_id"] != DeviceType.GHOST]
    device_ids = devices_df["device_id"].astype(int).tolist()

    # id ➜ long_name lookup
    name_by_id = dict(
        zip(
            devices_df["device_id"].astype(int),
            devices_df["name_long"].fillna(""),
        )
    )

    device_names: list[str | None] = [name_by_id.get(d) for d in device_ids]
    # Sort device_ids and device_names together using natural sort on device_names
    sorted_pairs = natsorted(zip(device_names, device_ids), key=lambda x: x[0] or "")
    if sorted_pairs:
        device_names, device_ids = map(list, zip(*sorted_pairs))  # type: ignore[assignment]
    device_names_y: list[str] = [".".join(str(n).split(".")[:-1]) for n in device_names]
    device_names_x: list[str] = [str(n).split(".")[-1] for n in device_names]

    # ── organize the data into {sensor_type_id: {device_id: value}} -------------
    values_by_sensor: dict[int, dict[int, float | None]] = {}
    times_by_sensor: dict[int, dict[int, datetime.datetime]] = {}

    for row in data_df.itertuples(index=False):
        sid = typing.cast(int, row.sensor_type_id)
        did = typing.cast(int, row.device_id)
        values_by_sensor.setdefault(sid, {})[did] = _extract_numeric_value_from_row(
            row=row
        )
        times_by_sensor.setdefault(sid, {})[did] = typing.cast(
            datetime.datetime, row.time
        )

    # ── fetch all sensor types at once for name_short lookup -------------------
    sensor_type_ids = list(values_by_sensor.keys())
    sensor_types = await get_sensor_types(
        sensor_type_ids=sensor_type_ids,
    ).get_async(output_type=OutputType.PANDAS)
    sensor_type_names = dict(
        zip(sensor_types["sensor_type_id"], sensor_types["name_short"])
    )

    # ── convert to front-end "traces" shape -------------------------------------
    traces: list[dict[str, str | list | int]] = []
    for sensor_type_id, values_by_device in values_by_sensor.items():
        traces.append(
            {
                "name": SENSOR_TYPE_NAME.get(
                    sensor_type_id,
                    f"Sensor {sensor_type_id}",
                ),
                "name_short": sensor_type_names.get(
                    sensor_type_id,
                    f"Sensor {sensor_type_id}",
                ),
                "sensor_type_id": sensor_type_id,
                "values": [values_by_device.get(did) for did in device_ids],
                "times": [
                    times_by_sensor[sensor_type_id].get(did, None) for did in device_ids
                ],
            },
        )

    # ── final RealTimeData payload ---------------------------------------------
    return {
        "device_ids": device_ids,
        "device_names": device_names,
        "device_names_x": device_names_x,
        "device_names_y": device_names_y,
        "traces": traces,
    }


# Device Type Power Summary Models and Endpoints
class DeviceTypePowerSummary(BaseModel):
    """Response model for device type power summary."""

    device_type_power: dict[int, float]  # device_type_id -> power in MW
    timestamp: str  # ISO timestamp of the data


@router.get(
    "/device-type-overview/power-summary",
    response_model=DeviceTypePowerSummary,
    response_class=ORJSONResponse,
)
async def get_device_type_power_summary(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    """Get power summary for all device types in the project.

        This endpoint efficiently calculates actual power for all device types
        using the same proven logic as the GIS and plotting endpoints.

    Args:
        project_db: TODO: describe.
        project: TODO: describe.
    """
    # Get all device types used in this project
    used_device_type_ids = getattr(project.spec, "used_device_type_ids", [])

    if not used_device_type_ids:
        return DeviceTypePowerSummary(
            device_type_power={}, timestamp=datetime.datetime.now().isoformat()
        )

    device_type_power = {}
    project_schema = utils.get_project_schema(project_db=project_db)

    # --- Optimized path: compute power sums for most device types in one query ---
    # We treat AC-power-like device types (PCS/MVT/Circuit/BESS PCS/MVT/Circuit, etc.)
    # as sum of latest sensor_type_id=PV_PCS_AC_POWER values, scaled by tag.unit_scale.
    # We exclude tracker rows (29) and PV DC Combiner (9) from this grouped query.

    ac_like_types = [
        dt
        for dt in used_device_type_ids
        if dt not in [DeviceType.TRACKER_ROW, DeviceType.PV_DC_COMBINER]
    ]

    if ac_like_types:
        # Build a single grouped query over DataTimeseriesLast -> Tag -> Device
        # numeric value = coalesce in priority order, cast to float
        value_num = func.coalesce(
            cast(models.DataTimeseriesLast.value_double, Float),
            cast(models.DataTimeseriesLast.value_real, Float),
            cast(models.DataTimeseriesLast.value_bigint, Float),
            cast(models.DataTimeseriesLast.value_integer, Float),
        )
        unit_scale = func.coalesce(models.Tag.unit_scale, 1.0)
        value_scaled = value_num * unit_scale

        query = (
            select(
                models.Device.device_type_id.label("device_type_id"),
                func.sum(value_scaled).label("power_sum"),
            )
            .select_from(models.Device)
            .join(models.Tag, models.Tag.device_id == models.Device.device_id)
            .join(
                models.DataTimeseriesLast,
                models.DataTimeseriesLast.tag_id == models.Tag.tag_id,
            )
            .where(models.Device.device_type_id == func.any(array(ac_like_types)))
            .where(models.Tag.sensor_type_id == SensorType.PV_PCS_AC_POWER.value)
            .group_by(models.Device.device_type_id)
        )

        try:
            rows = project_db.execute(query).all()
            for device_type_id, power_sum in rows:
                if power_sum is not None:
                    device_type_power[int(device_type_id)] = float(power_sum)
        except Exception as e:  # pragma: no cover - defensive path
            logger.error(f"Grouped AC-like power query failed: {e}")

    # --- Special case: PV DC Combiner (9) needs custom logic (current × voltage) ---
    if 9 in used_device_type_ids:
        try:
            # Fetch combiner devices once
            combiner_devices_df = await core.crud.project.devices.get_project_devices(
                device_type_ids=[DeviceType.PV_DC_COMBINER],
            ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
            device_ids = combiner_devices_df["device_id"].astype(int).tolist()
            if device_ids:
                power_sum = await _calculate_dc_combiner_power_sum(
                    project_db=project_db, device_ids=device_ids
                )
                if power_sum is not None:
                    device_type_power[9] = power_sum
        except Exception as e:  # pragma: no cover - defensive path
            logger.error(f"Error calculating combiner power: {e}")

    return DeviceTypePowerSummary(
        device_type_power=device_type_power,
        timestamp=datetime.datetime.now().isoformat(),
    )


async def _calculate_dc_combiner_power_sum(
    *, project_db: Session, device_ids: list[int]
) -> float | None:
    """Calculate total power for DC combiners using the proven utility_expected logic.

    Args:
        project_db: TODO: describe.
        project: TODO: describe.
        device_ids: TODO: describe.
    """
    if not device_ids:
        return None

    # Get device information
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_df = await core.crud.project.devices.get_project_devices(
        device_ids=device_ids
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    devices_df = devices_df.copy()
    devices_df["device_id"] = devices_df["device_id"].astype(int)
    devices_df["parent_device_id"] = devices_df["parent_device_id"].where(
        pd.notna(devices_df["parent_device_id"]), None
    )
    device_dict = devices_df.set_index("device_id").to_dict(orient="index")

    # Find parent PCS IDs
    parent_pcs_ids = [
        device_dict[dev_id]["parent_device_id"]
        for dev_id in device_ids
        if device_dict[dev_id]["parent_device_id"] is not None
    ]

    if not parent_pcs_ids:
        return None

    # Map combiners to their parent PCS ID
    combiner_to_parent_pcs_id = {
        dev_id: device_dict[dev_id]["parent_device_id"]
        for dev_id in device_ids
        if device_dict[dev_id]["parent_device_id"] is not None
    }

    # Get PV PCS Modules for voltage data
    all_pcs_modules_df = await core.crud.project.devices.get_project_devices(
        device_type_ids=[DeviceType.PV_PCS_MODULE],
        parent_device_ids=parent_pcs_ids,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    all_pcs_modules_df = all_pcs_modules_df.copy()
    all_pcs_modules_df["device_id"] = all_pcs_modules_df["device_id"].astype(int)
    all_pcs_modules_df["parent_device_id"] = all_pcs_modules_df[
        "parent_device_id"
    ].where(pd.notna(all_pcs_modules_df["parent_device_id"]), None)
    all_pcs_modules = list(all_pcs_modules_df.itertuples(index=False))

    module_ids = [typing.cast(int, mod.device_id) for mod in all_pcs_modules]

    # Build mapping from parent PCS ID to its module IDs
    parent_pcs_id_to_module_ids: dict[int, list[int]] = {}
    for mod in all_pcs_modules:
        pcs_id = mod.parent_device_id
        if pcs_id is not None:
            pcs_id_int = typing.cast(int, pcs_id)
            if pcs_id_int not in parent_pcs_id_to_module_ids:
                parent_pcs_id_to_module_ids[pcs_id_int] = []
            parent_pcs_id_to_module_ids[pcs_id_int].append(
                typing.cast(int, mod.device_id)
            )

    # Fetch latest currents at combiner level from timeseries_last
    df_current = await core.crud.project.data_timeseries_last.get_data_timeseries_last(
        device_ids=device_ids,
        sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT.value],
        deep=True,
        include_ghost_tags=False,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if df_current.empty:
        return None

    # Fetch latest voltages (prefer module voltage 38; fallback to PCS voltage 144)
    df_voltage_modules = pd.DataFrame()
    if module_ids:
        df_voltage_modules = (
            await core.crud.project.data_timeseries_last.get_data_timeseries_last(
                device_ids=module_ids,
                sensor_type_ids=[SensorType.PV_PCS_MODULE_DC_VOLTAGE.value],
                deep=True,
                include_ghost_tags=False,
            ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        )

    using_pcs_level_voltage = False
    df_voltage_pcs = pd.DataFrame()
    if df_voltage_modules.empty:
        df_voltage_pcs = (
            await core.crud.project.data_timeseries_last.get_data_timeseries_last(
                device_ids=[pid for pid in parent_pcs_ids if pid is not None],
                sensor_type_ids=[SensorType.PV_PCS_DC_VOLTAGE.value],
                deep=True,
                include_ghost_tags=False,
            ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        )
        using_pcs_level_voltage = True

    if df_voltage_modules.empty and df_voltage_pcs.empty:
        return None

    # Build value maps (extract numeric with unit_scale)
    current_by_combiner: dict[int, float] = {}
    for row in df_current.itertuples(index=False):
        value = _extract_numeric_value_from_row(row=row)
        if value is not None:
            current_by_combiner[typing.cast(int, row.device_id)] = value

    voltage_by_module: dict[int, float] = {}
    for row in df_voltage_modules.itertuples(index=False):
        value = _extract_numeric_value_from_row(row=row)
        if value is not None:
            voltage_by_module[typing.cast(int, row.device_id)] = value

    voltage_by_pcs: dict[int, float] = {}
    for row in df_voltage_pcs.itertuples(index=False):
        value = _extract_numeric_value_from_row(row=row)
        if value is not None:
            voltage_by_pcs[typing.cast(int, row.device_id)] = value

    # Calculate power for each combiner using last values
    total_power_MW = 0.0
    multiplier = 1 / 1_000_000  # V * A = W -> MW

    for combiner_id in device_ids:
        parent_pcs_id = combiner_to_parent_pcs_id.get(combiner_id)
        if parent_pcs_id is None:
            continue

        current_a = current_by_combiner.get(combiner_id)
        if current_a is None:
            continue

        # Pick voltage
        if not using_pcs_level_voltage:
            module_ids_for_parent = parent_pcs_id_to_module_ids.get(parent_pcs_id, [])
            voltages = [
                voltage_by_module[mid]
                for mid in module_ids_for_parent
                if mid in voltage_by_module
            ]
            voltage_v = sum(voltages) / len(voltages) if voltages else None
        else:
            voltage_v = voltage_by_pcs.get(parent_pcs_id)

        if voltage_v is None:
            continue

        total_power_MW += (voltage_v * current_a) * multiplier

    return total_power_MW
