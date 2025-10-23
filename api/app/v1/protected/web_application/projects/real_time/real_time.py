import datetime
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy import Float, cast, func
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from app._crud.operational.sensor_types import get_sensor_types
from app._crud.projects.data_timeseries_latest import (
    get_data_timeseries_latest_by_device_type,
)
from app.dependencies import get_project_db
from core import models

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/real-time",
    tags=["real-time"],
    include_in_schema=utils.get_include_in_schema(),
)


# --- 1) helper to convert a DataTimeseriesLast row into a single float -------------
def _extract_numeric_value(*, row) -> float | None:
    """Return the first non-NULL numeric column from a DataTimeseriesLast row."""
    # todo: unit_offset is not applied in this function however it should probably be
    # applied in the get_data_timeseries_latest_by_device_type function instead
    for attr in (
        "value_integer",
        "value_bigint",
        "value_real",
        "value_double",
    ):
        value = getattr(row, attr)
        if value is not None:
            value = float(value)
            if row.tag.unit_scale is not None:
                value = value * row.tag.unit_scale
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
}


# --- 3) the endpoint ----------------------------------------------------------------
@router.get("/{device_type_id}", response_class=ORJSONResponse)
def get_by_device_type_id(
    device_type_id: int,
    sensor_type_ids: Annotated[list[int] | None, Query()] = None,
    project_db: Session = Depends(get_project_db),
):
    # ── fetch latest values ─────────────────────────────────────────────────────
    data_rows = get_data_timeseries_latest_by_device_type(
        db=project_db,
        device_type_id=device_type_id,
        sensor_type_ids=sensor_type_ids,
        start=None,
    )

    if not data_rows:
        return {  # empty stub so TS side stays happy
            "device_ids": [],
            "device_names": [],
            "device_names_x": [],
            "device_names_y": [],
            "traces": [],
        }

    # ── build *unique* device list in deterministic order ───────────────────────
    device_ids: list[int] = []
    seen = set()
    for row in data_rows:
        did = row.tag.device_id
        if did not in seen:
            seen.add(did)
            device_ids.append(did)

    # ── device metadata (names) --------------------------------------------------
    devices = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_ids=device_ids,
        deep=False,
    ).models()
    devices = [d for d in devices if d.device_type_id != 0]
    device_ids = [d.device_id for d in devices]

    # id ➜ long_name lookup
    name_by_id = {d.device_id: d.name_long for d in devices}

    device_names: list[str | None] = [name_by_id[d] for d in device_ids]
    # device_names = natsorted(device_names)
    device_names_y: list[str] = [".".join(str(n).split(".")[:-1]) for n in device_names]
    device_names_x: list[str] = [str(n).split(".")[-1] for n in device_names]

    # ── organize the data into {sensor_type_id: {device_id: value}} -------------
    values_by_sensor: dict[int, dict[int, float | None]] = {}
    times_by_sensor: dict[int, dict[int, datetime.datetime]] = {}
    for row in data_rows:
        sid = row.tag.sensor_type_id
        did = row.tag.device_id
        values_by_sensor.setdefault(sid, {})[did] = _extract_numeric_value(row=row)
        times_by_sensor.setdefault(sid, {})[did] = row.time

    # ── fetch all sensor types at once for name_short lookup -------------------
    sensor_type_ids = list(values_by_sensor.keys())
    sensor_types = get_sensor_types(
        db=project_db,
        sensor_type_ids=sensor_type_ids,
    )
    sensor_type_names = {st.sensor_type_id: st.name_short for st in sensor_types}

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
def get_device_type_power_summary(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project)],
):
    """
    Get power summary for all device types in the project.

    This endpoint efficiently calculates actual power for all device types
    using the same proven logic as the GIS and plotting endpoints.
    """
    # Get all device types used in this project
    used_device_type_ids = getattr(project.spec, "used_device_type_ids", [])

    if not used_device_type_ids:
        return DeviceTypePowerSummary(
            device_type_power={}, timestamp=datetime.datetime.now().isoformat()
        )

    device_type_power = {}

    # --- Optimized path: compute power sums for most device types in one query ---
    # We treat AC-power-like device types (PCS/MVT/Circuit/BESS PCS/MVT/Circuit, etc.)
    # as sum of latest sensor_type_id=2 values, scaled by tag.unit_scale.
    # We exclude tracker rows (29) and PV DC Combiner (9) from this grouped query.

    ac_like_types = [dt for dt in used_device_type_ids if dt not in [29, 9]]

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

        q = (
            project_db.query(
                models.Device.device_type_id.label("device_type_id"),
                func.sum(value_scaled).label("power_sum"),
            )
            .join(models.Tag, models.Tag.device_id == models.Device.device_id)
            .join(
                models.DataTimeseriesLast,
                models.DataTimeseriesLast.tag_id == models.Tag.tag_id,
            )
            .filter(models.Device.device_type_id == func.any(array(ac_like_types)))
            .filter(models.Tag.sensor_type_id == 2)
            .group_by(models.Device.device_type_id)
        )

        try:
            rows = q.all()
            for device_type_id, power_sum in rows:
                if power_sum is not None:
                    device_type_power[int(device_type_id)] = float(power_sum)
        except Exception as e:  # pragma: no cover - defensive path
            logger.error(f"Grouped AC-like power query failed: {e}")

    # --- Special case: PV DC Combiner (9) needs custom logic (current × voltage) ---
    if 9 in used_device_type_ids:
        try:
            # Fetch combiner devices once
            combiner_devices = core.crud.project.devices.get_project_devices(
                project_db,
                device_type_ids=[9],
            ).models()
            device_ids = [d.device_id for d in combiner_devices]
            if device_ids:
                power_sum = _calculate_dc_combiner_power_sum(
                    project_db=project_db, project=project, device_ids=device_ids
                )
                if power_sum is not None:
                    device_type_power[9] = power_sum
        except Exception as e:  # pragma: no cover - defensive path
            logger.error(f"Error calculating combiner power: {e}")

    return DeviceTypePowerSummary(
        device_type_power=device_type_power,
        timestamp=datetime.datetime.now().isoformat(),
    )


def _calculate_dc_combiner_power_sum(
    *, project_db: Session, project: models.Project, device_ids: list[int]
) -> float | None:
    """
    Calculate total power for DC combiners using the proven utility_expected logic.
    """
    if not device_ids:
        return None

    # Get device information
    device_dict = {
        device.device_id: device
        for device in core.crud.project.devices.get_project_devices(
            project_db, device_ids=device_ids
        ).models()
    }

    # Find parent PCS IDs
    parent_pcs_ids = [
        device_dict[dev_id].parent_device_id
        for dev_id in device_ids
        if device_dict[dev_id].parent_device_id is not None
    ]

    if not parent_pcs_ids:
        return None

    # Map combiners to their parent PCS ID
    combiner_to_parent_pcs_id = {
        dev_id: device_dict[dev_id].parent_device_id
        for dev_id in device_ids
        if device_dict[dev_id].parent_device_id is not None
    }

    # Get PV PCS Modules for voltage data
    all_pcs_modules = core.crud.project.devices.get_project_devices(
        project_db,
        device_type_ids=[3],  # PV PCS Module
        parent_device_ids=parent_pcs_ids,
    ).models()

    module_ids = [mod.device_id for mod in all_pcs_modules]

    # Build mapping from parent PCS ID to its module IDs
    parent_pcs_id_to_module_ids: dict[int, list[int]] = {}
    for mod in all_pcs_modules:
        pcs_id = mod.parent_device_id
        if pcs_id is not None:
            if pcs_id not in parent_pcs_id_to_module_ids:
                parent_pcs_id_to_module_ids[pcs_id] = []
            parent_pcs_id_to_module_ids[pcs_id].append(mod.device_id)

    # Fetch latest currents at combiner level from timeseries_last
    rows_current = core.crud.project.data_timeseries_last.get_data_timeseries_last(
        project_db,
        device_ids=device_ids,
        sensor_type_ids=[27],  # PV DC Combiner Current (A)
        deep=True,
        include_ghost_tags=False,
    ).models()

    if not rows_current:
        return None

    # Fetch latest voltages (prefer module voltage 38; fallback to PCS voltage 144)
    rows_voltage_modules = []
    if module_ids:
        rows_voltage_modules = (
            core.crud.project.data_timeseries_last.get_data_timeseries_last(
                project_db,
                device_ids=module_ids,
                sensor_type_ids=[38],  # PV PCS Module DC Voltage (V)
                deep=True,
                include_ghost_tags=False,
            ).models()
        )

    using_pcs_level_voltage = False
    rows_voltage_pcs = []
    if not rows_voltage_modules:
        rows_voltage_pcs = (
            core.crud.project.data_timeseries_last.get_data_timeseries_last(
                project_db,
                device_ids=[pid for pid in parent_pcs_ids if pid is not None],
                sensor_type_ids=[144],  # PV PCS DC Voltage (V)
                deep=True,
                include_ghost_tags=False,
            ).models()
        )
        using_pcs_level_voltage = True

    if not rows_voltage_modules and not rows_voltage_pcs:
        return None

    # Build value maps (extract numeric with unit_scale)
    current_by_combiner: dict[int, float] = {}
    for row in rows_current:
        value = _extract_numeric_value(row=row)
        if value is not None:
            current_by_combiner[row.tag.device_id] = value

    voltage_by_module: dict[int, float] = {}
    for row in rows_voltage_modules:
        value = _extract_numeric_value(row=row)
        if value is not None:
            voltage_by_module[row.tag.device_id] = value

    voltage_by_pcs: dict[int, float] = {}
    for row in rows_voltage_pcs:
        value = _extract_numeric_value(row=row)
        if value is not None:
            voltage_by_pcs[row.tag.device_id] = value

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


def _calculate_pcs_power_sum(
    *, project_db: Session, project: models.Project, device_ids: list[int]
) -> float | None:
    """Calculate total power for PV PCS devices using latest values (timeseries_last)."""
    if not device_ids:
        logger.debug("No device IDs provided for PCS power calculation")
        return None

    try:
        rows = core.crud.project.data_timeseries_last.get_data_timeseries_last(
            project_db,
            device_ids=device_ids,
            sensor_type_ids=[2],  # PV PCS AC Power (MW)
            deep=True,
            include_ghost_tags=False,
        ).models()

        if not rows:
            logger.debug(f"No latest PCS rows found for devices {device_ids}")
            return None

        # Sum MW values; convert to MW
        total_MW = 0.0
        for row in rows:
            value = _extract_numeric_value(row=row)
            if value is not None:
                total_MW += float(value)

        if total_MW <= 0:
            return None

        return total_MW
    except Exception as e:
        logger.error(
            f"Error in PCS power calculation (timeseries_last) for devices {device_ids}: {e}"
        )
        return None


def _calculate_mvt_power_sum(
    *, project_db: Session, project: models.Project, device_ids: list[int]
) -> float | None:
    """Calculate total power for PV MVT devices using Block AC Power (sensor_type_id=16).

    Each PV Block (type 6) corresponds to one PV MVT (type 15). We therefore
    sum the latest PV Block AC Power values for blocks that correspond to the
    given MVT device IDs.
    """
    if not device_ids:
        return None

    try:
        # Fetch blocks that correspond to these MVTs: blocks have parent_device_id == MVT id
        blocks = core.crud.project.devices.get_project_devices(
            project_db,
            device_type_ids=[6],  # PV Block
            parent_device_ids=[
                device_id for device_id in device_ids if device_id is not None
            ],
        ).models()

        if not blocks:
            return None

        block_ids = [b.device_id for b in blocks]

        # Fetch latest Block AC Power (sensor_type_id=16)
        rows = core.crud.project.data_timeseries_last.get_data_timeseries_last(
            project_db,
            device_ids=block_ids,
            sensor_type_ids=[16],  # PV Block AC Power (MW)
            deep=True,
            include_ghost_tags=False,
        ).models()

        if not rows:
            return None

        total_MW = 0.0
        for row in rows:
            value = _extract_numeric_value(row=row)
            if value is not None:
                total_MW += float(value)

        if total_MW <= 0:
            return None

        return total_MW
    except Exception:
        return None


def _calculate_circuit_power_sum(
    *, project_db: Session, project: models.Project, device_ids: list[int]
) -> float | None:
    """Calculate total power for PV Circuit devices (try meter first, then PCS)."""
    if not device_ids:
        return None

    # Try meter data first
    meter_tags = core.crud.project.tags.get_project_tags(
        project_db,
        device_ids=device_ids,
        sensor_type_ids=[1],  # Meter Active Power
    ).models()

    if meter_tags:
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(
            hours=1
        )  # Increased from 5 minutes to 1 hour

        try:
            df_data = utils.data_df(
                project_db,
                project,
                tags=meter_tags,
                start=start_time,
                end=end_time,
            )

            if not df_data.empty:
                total_power_MW = df_data.sum().sum()
                logger.debug(
                    f"Circuit power calculation (meter): total_power_MW={total_power_MW}, device_ids={device_ids}"
                )
                return float(total_power_MW)
        except Exception as e:
            logger.error(
                f"Error in circuit power calculation (meter) for devices {device_ids}: {e}"
            )

    # Fallback to PCS data
    pcs_tags = core.crud.project.tags.get_project_tags(
        project_db,
        device_ids=device_ids,
        sensor_type_ids=[2],  # PV PCS AC Power
    ).models()

    if not pcs_tags:
        logger.debug(f"No PCS tags found for circuit devices {device_ids}")
        return None

    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(
        hours=1
    )  # Increased from 5 minutes to 1 hour

    try:
        df_data = utils.data_df(
            project_db,
            project,
            tags=pcs_tags,
            start=start_time,
            end=end_time,
        )

        if df_data.empty:
            logger.debug(
                f"No data found for circuit devices {device_ids} (PCS fallback) in time range {start_time} to {end_time}"
            )
            return None

        total_power_MW = df_data.sum().sum()
        logger.debug(
            f"Circuit power calculation (PCS fallback): total_power_MW={total_power_MW}, device_ids={device_ids}"
        )
        return float(total_power_MW)
    except Exception as e:
        logger.error(
            f"Error in circuit power calculation (PCS fallback) for devices {device_ids}: {e}"
        )
        return None


def _calculate_bess_power_sum(
    *,
    project_db: Session,
    project: models.Project,
    device_ids: list[int],
    device_type_id: int,
) -> float | None:
    """Calculate total power for BESS devices."""
    if not device_ids:
        return None

    # Map device types to sensor types
    sensor_type_map = {
        17: [1],  # BESS Circuit - Meter Active Power
        25: [1],  # BESS MVT - Meter Active Power
        13: [1],  # BESS PCS - Meter Active Power
    }

    sensor_type_ids = sensor_type_map.get(device_type_id, [1])

    tags = core.crud.project.tags.get_project_tags(
        project_db,
        device_ids=device_ids,
        sensor_type_ids=sensor_type_ids,
    ).models()

    if not tags:
        return None

    # Get latest data
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(
        hours=1
    )  # Increased from 5 minutes to 1 hour

    try:
        df_data = utils.data_df(
            project_db,
            project,
            tags=tags,
            start=start_time,
            end=end_time,
        )

        if df_data.empty:
            logger.debug(
                f"No data found for BESS devices {device_ids} in time range {start_time} to {end_time}"
            )
            return None

        # Sum all power values and convert to MW
        total_power_MW = df_data.sum().sum()
        logger.debug(
            f"BESS power calculation: total_power_MW={total_power_MW}, device_ids={device_ids}"
        )
        return float(total_power_MW)
    except Exception as e:
        logger.error(f"Error in BESS power calculation for devices {device_ids}: {e}")
        return None


def _calculate_generic_power_sum(
    *,
    project_db: Session,
    project: models.Project,
    device_ids: list[int],
    device_type_id: int,
) -> float | None:
    """Calculate power for other device types if power data is available."""
    if not device_ids:
        return None

    # Try common power sensor types
    power_sensor_types = [1, 2]  # Meter Active Power, PV PCS AC Power

    for sensor_type_id in power_sensor_types:
        tags = core.crud.project.tags.get_project_tags(
            project_db,
            device_ids=device_ids,
            sensor_type_ids=[sensor_type_id],
        ).models()

        if tags:
            end_time = datetime.datetime.now()
            start_time = end_time - datetime.timedelta(
                hours=1
            )  # Increased from 5 minutes to 1 hour

            try:
                df_data = utils.data_df(
                    project_db,
                    project,
                    tags=tags,
                    start=start_time,
                    end=end_time,
                )

                if not df_data.empty:
                    total_power_MW = df_data.sum().sum()
                    logger.debug(
                        f"Generic power calculation: total_power_MW={total_power_MW}, device_ids={device_ids}, sensor_type_id={sensor_type_id}"
                    )
                    return float(total_power_MW)
            except Exception as e:
                logger.error(
                    f"Error in generic power calculation for devices {device_ids}, sensor_type_id={sensor_type_id}: {e}"
                )
                continue

    return None
