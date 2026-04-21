import datetime
import typing
from typing import Annotated

import pandas as pd
import polars as pl
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import DeviceType, KPIType, ProjectStatusType, SensorType
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

import core
from app import dependencies, interfaces, logger, utils
from app.v1.operational.kpi_data import get_kpi_data_helper
from core import models

router = APIRouter(
    prefix="/{project_id}",
    tags=["gis"],
    dependencies=[Depends(dependencies.check_project_access_async)],
    include_in_schema=utils.get_include_in_schema(),
)


def _get_row_value(*, row: typing.Any, key: str) -> typing.Any:
    """Read a value from either a namedtuple row or dict-like row.

    Args:
        row: Query row returned from pandas/polars conversion helpers.
        key: Column name to fetch from the row.
    """
    if hasattr(row, key):
        return getattr(row, key)
    if isinstance(row, dict):
        return row.get(key)
    return None


def _get_row_timestamp_iso(*, row: typing.Any) -> str | None:
    """Return an ISO timestamp from a row's time column.

    Args:
        row: Query row containing a time field.
    """
    time_raw = _get_row_value(row=row, key="time")
    if time_raw is None or pd.isna(time_raw):
        return None

    timestamp = pd.to_datetime(time_raw, errors="coerce", utc=True)
    if pd.isna(timestamp):
        return None

    return typing.cast(str, timestamp.isoformat())


def _get_scaled_data_timeseries_last_value(*, row: typing.Any) -> float | None:
    """Return the latest numeric value from a data_timeseries_last row.

    Args:
        row: Query row containing value columns and unit metadata.
    """
    raw_value: float | None = None
    for col in ("value_integer", "value_bigint", "value_real", "value_double"):
        candidate = _get_row_value(row=row, key=col)
        if pd.notna(candidate):
            raw_value = float(candidate)
            break

    if raw_value is None:
        return None

    scale_raw = _get_row_value(row=row, key="unit_scale")
    offset_raw = _get_row_value(row=row, key="unit_offset")
    scale = float(scale_raw) if pd.notna(scale_raw) else 1.0
    offset = float(offset_raw) if pd.notna(offset_raw) else 0.0
    return raw_value * scale + offset


async def _get_latest_scaled_sensor_values_by_device(
    *,
    device_ids: list[int],
    sensor_type_ids: list[int],
    project_schema: str,
    multiplier: float = 1.0,
) -> dict[int, tuple[str | None, float | None]]:
    """Fetch the latest scaled value for each device from data_timeseries_last.

    Args:
        device_ids: Device ids to query.
        sensor_type_ids: Sensor types that identify the desired measurement.
        project_schema: Project schema for the query execution.
        multiplier: Optional multiplier applied after scaling the raw value.
    """
    latest_df = await core.crud.project.data_timeseries_last.get_data_timeseries_last(
        device_ids=device_ids,
        sensor_type_ids=sensor_type_ids,
        deep=True,
        include_ghost_tags=False,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    latest_values: dict[int, tuple[str | None, float | None]] = {}
    for row in latest_df.itertuples(index=False):
        device_id = _get_row_value(row=row, key="device_id")
        if pd.isna(device_id):
            continue

        value = _get_scaled_data_timeseries_last_value(row=row)
        latest_values[int(device_id)] = (
            _get_row_timestamp_iso(row=row),
            value * multiplier if value is not None else None,
        )

    return latest_values


async def _get_latest_combiner_power_by_device(
    *,
    device_ids: list[int],
    device_dict: dict[int, typing.Any],
    project_schema: str,
) -> dict[int, tuple[str | None, float | None]]:
    """Calculate latest combiner power from latest current and voltage values.

    Args:
        device_ids: Combiner device ids to calculate power for.
        device_dict: Mapping of combiner id to validated device row.
        project_schema: Project schema for CRUD queries.
    """
    parent_ids = {
        device_dict[dev_id].parent_device_id
        for dev_id in device_ids
        if device_dict[dev_id].parent_device_id is not None
    }
    if not parent_ids:
        return {}

    parent_device_ids = list(parent_ids)
    parent_devices_df = await core.crud.project.devices.get_project_devices(
        device_ids=[typing.cast(int, pid) for pid in parent_device_ids],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    parent_devices_df = parent_devices_df.copy()
    parent_devices_df["device_id"] = parent_devices_df["device_id"].astype(int)
    parent_devices_df["device_type_id"] = parent_devices_df["device_type_id"].astype(
        int
    )
    parent_devices_df["parent_device_id"] = parent_devices_df["parent_device_id"].apply(
        lambda value: None if pd.isna(value) else value
    )
    parent_device_dict = {
        typing.cast(int, row.device_id): row
        for row in parent_devices_df.itertuples(index=False)
    }

    parent_pcs_ids: list[int] = []
    combiner_to_parent_pcs_id: dict[int, int] = {}
    for dev_id in device_ids:
        parent_id = device_dict[dev_id].parent_device_id
        if parent_id is None:
            continue

        parent_device = parent_device_dict.get(typing.cast(int, parent_id))
        if parent_device is None:
            continue

        if parent_device.device_type_id == DeviceType.PV_INVERTER_MODULE:
            pcs_id = parent_device.parent_device_id
            if pcs_id is not None:
                parent_pcs_ids.append(typing.cast(int, pcs_id))
                combiner_to_parent_pcs_id[dev_id] = typing.cast(int, pcs_id)
        elif parent_device.device_type_id == DeviceType.PV_INVERTER:
            parent_pcs_ids.append(typing.cast(int, parent_id))
            combiner_to_parent_pcs_id[dev_id] = typing.cast(int, parent_id)

    parent_pcs_ids = list(set(parent_pcs_ids))
    if not parent_pcs_ids:
        return {}

    all_pcs_modules_df = await core.crud.project.devices.get_project_devices(
        device_type_ids=[DeviceType.PV_INVERTER_MODULE],
        parent_device_ids=[typing.cast(int, pid) for pid in parent_pcs_ids],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    all_pcs_modules_df = all_pcs_modules_df.copy()
    all_pcs_modules_df["device_id"] = all_pcs_modules_df["device_id"].astype(int)
    all_pcs_modules_df["parent_device_id"] = all_pcs_modules_df[
        "parent_device_id"
    ].apply(lambda value: None if pd.isna(value) else value)
    parent_pcs_id_to_module_ids: dict[int, list[int]] = {}
    module_ids: list[int] = []
    for row in all_pcs_modules_df.itertuples(index=False):
        module_ids.append(typing.cast(int, row.device_id))
        pcs_id = row.parent_device_id
        if pcs_id is None:
            continue
        parent_pcs_id_to_module_ids.setdefault(typing.cast(int, pcs_id), []).append(
            typing.cast(int, row.device_id)
        )

    latest_current_by_combiner = await _get_latest_scaled_sensor_values_by_device(
        device_ids=device_ids,
        sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT.value],
        project_schema=project_schema,
    )
    if not latest_current_by_combiner:
        return {}

    voltage_by_module: dict[int, float] = {}
    if module_ids:
        latest_voltage_by_module = await _get_latest_scaled_sensor_values_by_device(
            device_ids=module_ids,
            sensor_type_ids=[SensorType.PV_INVERTER_MODULE_DC_VOLTAGE.value],
            project_schema=project_schema,
        )
        voltage_by_module = {
            device_id: value
            for device_id, (_, value) in latest_voltage_by_module.items()
            if value is not None
        }

    voltage_by_pcs: dict[int, float] = {}
    using_pcs_level_voltage = not voltage_by_module
    if using_pcs_level_voltage:
        latest_voltage_by_pcs = await _get_latest_scaled_sensor_values_by_device(
            device_ids=parent_pcs_ids,
            sensor_type_ids=[SensorType.PV_INVERTER_DC_VOLTAGE.value],
            project_schema=project_schema,
        )
        voltage_by_pcs = {
            device_id: value
            for device_id, (_, value) in latest_voltage_by_pcs.items()
            if value is not None
        }
        if not voltage_by_pcs:
            return {}

    latest_power_by_combiner: dict[int, tuple[str | None, float | None]] = {}
    for dev_id in device_ids:
        parent_pcs_id = combiner_to_parent_pcs_id.get(dev_id)
        if parent_pcs_id is None:
            continue

        time_iso, current_a = latest_current_by_combiner.get(dev_id, (None, None))
        if current_a is None:
            continue

        voltage_v: float | None = None
        if using_pcs_level_voltage:
            voltage_v = voltage_by_pcs.get(parent_pcs_id)
        else:
            module_ids_for_parent = parent_pcs_id_to_module_ids.get(parent_pcs_id, [])
            voltages = [
                voltage_by_module[module_id]
                for module_id in module_ids_for_parent
                if module_id in voltage_by_module
            ]
            if voltages:
                voltage_v = sum(voltages) / len(voltages)

        if voltage_v is None:
            continue

        latest_power_by_combiner[dev_id] = (
            time_iso,
            (voltage_v * current_a) / 1_000,
        )

    return latest_power_by_combiner


async def _get_latest_expected_power_by_device(
    *,
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: list[int],
    expected_metric_ids_fallback: list[int],
    project: models.Project,
    project_schema: str,
) -> tuple[dict[int, tuple[str | None, float | None]], dict[int, list[str]]]:
    """Fetch the latest expected power per device using existing metric fallbacks.

    Args:
        start: Start of the expected-power query window.
        end: End of the expected-power query window.
        device_ids: Device ids to fetch expected power for.
        expected_metric_ids_fallback: Expected metric ids ordered by preference.
        project: Project model used for timezone conversion.
        project_schema: Project schema for CRUD queries.
    """
    if not expected_metric_ids_fallback:
        return {}, {}

    data_expected = None
    found_metric_id = None
    for expected_metric_id in expected_metric_ids_fallback:
        data_expected = await core.crud.project.data_expected.get_project_data_expected(
            start=start,
            end=end,
            device_ids=device_ids,
            expected_metric_ids=[expected_metric_id],
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        if not data_expected.empty:
            found_metric_id = expected_metric_id
            break

    if data_expected is None or data_expected.empty or found_metric_id is None:
        return {}, {}

    df_expected = data_expected.copy()
    df_expected["time"] = pd.to_datetime(df_expected["time"], errors="coerce")
    if getattr(df_expected["time"].dt, "tz", None) is None:
        df_expected["time"] = df_expected["time"].dt.tz_localize(
            "UTC",
            nonexistent="NaT",
            ambiguous="NaT",
        )
    df_expected["time"] = df_expected["time"].dt.tz_convert(project.time_zone)
    df_expected = df_expected.dropna(subset=["time"]).sort_values("time")
    if df_expected.empty:
        return {}, {}

    latest_expected_rows = df_expected.groupby("device_id", as_index=False).tail(1)
    latest_expected_by_device: dict[int, tuple[str | None, float | None]] = {}
    for row in latest_expected_rows.itertuples(index=False):
        row_dev_id = getattr(row, "device_id", None)
        if pd.isna(row_dev_id):
            continue
        dev_id_int = int(typing.cast(int, row_dev_id))
        row_val = getattr(row, "value", None)
        power_kw = (
            float(typing.cast(int | float, row_val)) / 1_000
            if row_val is not None and pd.notna(row_val)
            else None
        )
        time_raw = getattr(row, "time", None)
        if time_raw is None or pd.isna(time_raw):
            time_iso = None
        else:
            time_ts = pd.to_datetime(
                typing.cast(
                    datetime.datetime | pd.Timestamp | str | float | int,
                    time_raw,
                ),
                errors="coerce",
                utc=True,
            )
            time_iso = (
                None if pd.isna(time_ts) else typing.cast(str, time_ts.isoformat())
            )
        latest_expected_by_device[dev_id_int] = (time_iso, power_kw)

    unique_versions_by_device: dict[int, list[str]] = {}
    for device_id, df_device in df_expected.groupby("device_id"):
        unique_versions_by_device[int(typing.cast(int, device_id))] = sorted(
            df_device["version"].dropna().unique().tolist()
        )

    return latest_expected_by_device, unique_versions_by_device


def _build_single_point_power_results(
    *,
    device_ids: list[int],
    actual_by_device: dict[int, tuple[str | None, float | None]],
    expected_by_device: dict[int, tuple[str | None, float | None]],
    unique_versions_by_device: dict[int, list[str]],
) -> dict[int, dict[str, typing.Any]]:
    """Build the existing GIS power payload using only the latest sample.

    Args:
        device_ids: Device ids to include in the payload.
        actual_by_device: Latest actual time/value keyed by device id.
        expected_by_device: Latest expected time/value keyed by device id.
        unique_versions_by_device: Expected-data versions keyed by device id.
    """
    results: dict[int, dict[str, typing.Any]] = {}
    for dev_id in device_ids:
        actual_time_iso, actual_power = actual_by_device.get(dev_id, (None, None))
        expected_time_iso, expected_power = expected_by_device.get(
            dev_id,
            (None, None),
        )
        time_iso = actual_time_iso or expected_time_iso

        results[dev_id] = {
            "times": [time_iso] if time_iso is not None else [],
            "actual": {"power": [actual_power]},
            "expected_soiled": {
                "power": [expected_power],
                "unique_versions": unique_versions_by_device.get(dev_id, []),
            },
        }

    return results


@router.get("/tracker-by-block/{block_id}", response_model=interfaces.GeoJSON)
async def get_tracker_by_block(
    *,
    block_id: int,
    start: datetime.date,
    end: datetime.date,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    # Get tracker rows which are descendents of the block
    """todo

    Args:
        block_id: Description for block_id.
        start: Description for start.
        end: Description for end.
        project_db: Description for project_db.
        project: Description for project.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_df = await core.crud.project.devices.get_project_devices(
        device_type_ids=[DeviceType.TRACKER_ROW],
        device_id_descendent_of=block_id,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    # Get KPI data
    kpi_data_dict = utils.kpi_data_list_to_dict(
        kpi_data=get_kpi_data_helper(
            db=project_db,
            start=start,
            end=end,
            kpi_type_ids=[
                KPIType.TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_ROW,
                KPIType.TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_ROW,
            ],
            project_ids=[project.project_id],
            include_device_data=True,
        ),
        key="kpi_type_id",
    )

    # Look for KPI data by KPI type id
    kpi_data_pos_row = kpi_data_dict.get(21)
    kpi_data_sp_row = kpi_data_dict.get(22)

    # If KPI data is not found, use empty Series
    if kpi_data_pos_row is None or kpi_data_sp_row is None:
        s_pos_row, s_sp_row = pd.Series(), pd.Series()

    # If KPI data is found, parse the data and take the mean
    else:
        s_pos_row = (
            utils.parse_kpi_data_to_df(kpi_data=kpi_data_pos_row)
            .apply(pd.to_numeric, errors="coerce")
            .mean()
            .astype(float)
            .round(2)
        )
        s_sp_row = (
            utils.parse_kpi_data_to_df(kpi_data=kpi_data_sp_row)
            .apply(pd.to_numeric, errors="coerce")
            .mean()
            .astype(float)
            .round(2)
        )

    # Create GeoJSON data
    return_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": device.get("name_long"),
                    "position_deviation": s_pos_row.get(int(device["device_id"])),
                    "setpoint_deviation": s_sp_row.get(int(device["device_id"])),
                },
                "geometry": device.get("polygon"),
            }
            for device in devices_df.to_dict("records")
        ],
    }

    return return_data


@router.get("/bess-enclosure", response_model=interfaces.GeoJSON)
async def get_bess_enclosure(
    *,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    # BESS Enclosure devices
    """todo

    Args:
        project_db: Description for project_db.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_df = await core.crud.project.devices.get_project_devices(
        device_type_ids=[DeviceType.BESS_ENCLOSURE]
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    features = [
        {
            "type": "Feature",
            "properties": {
                "name_long": device.get("name_long"),
            },
            "geometry": device.get("polygon"),
        }
        for device in devices_df.to_dict("records")
    ]

    return_data = {
        "type": "FeatureCollection",
        "features": features,
    }

    return return_data


@router.get("/devices-in-viewport")
async def get_devices_in_viewport(
    *,
    device_type_ids: Annotated[list[int] | None, Query()] = None,
    power_device_type_id: Annotated[int | None, Query()] = None,
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project_api),
):
    """Retrieves devices for the site, optionally filtered by device type.

    If power_device_type_id is provided, fetches and includes latest
    actual/expected power for devices matching that type.

    Args:
        device_type_ids: Description for device_type_ids.
        power_device_type_id: Description for power_device_type_id.
        project_db: Description for project_db.
        project: Description for project.
    """
    query = select(models.Device)

    # Optional filter by general device type IDs
    if device_type_ids:
        query = query.where(models.Device.device_type_id.in_(device_type_ids))

    # Execute the query
    devices = project_db.execute(query).scalars().all()

    # --- Optional Additional Data Fetching (Power or Tracker Angle) ---
    # This will hold data like: {device_id: {"actual": ..., "expected_soiled": ...}} or
    # {device_id: {"tracker_angle": ...}}
    all_device_extra_data = {}

    # 1. Fetch data for the primary power_device_type_id
    if power_device_type_id is not None:
        primary_data_device_ids = [
            dev.device_id
            for dev in devices
            if dev.device_type_id == power_device_type_id
        ]
        if primary_data_device_ids:
            try:
                primary_extra_data = await utility_expected(
                    device_ids=primary_data_device_ids,
                    project_db=project_db,
                    project=project,
                )
                all_device_extra_data.update(primary_extra_data)
            except Exception as e:  # Catch a broader range of exceptions
                logger.logger.error(
                    "Error fetching primary additional data for type "
                    f"{power_device_type_id}: {e}"
                )

    # 2. Fetch power data for any PCS (type 2) devices if not already fetched as primary
    if (
        power_device_type_id != DeviceType.PV_INVERTER
    ):  # Check if PCS wasn't the primary type
        # Identify PCS devices that are in the viewport AND don't already have
        # their data fetched
        pcs_to_fetch_ids = [
            dev.device_id
            for dev in devices
            if dev.device_type_id == DeviceType.PV_INVERTER
            and dev.device_id not in all_device_extra_data
        ]
        if pcs_to_fetch_ids:
            try:
                pcs_extra_data = await utility_expected(
                    device_ids=list(set(pcs_to_fetch_ids)),  # Ensure unique IDs
                    project_db=project_db,
                    project=project,
                )
                all_device_extra_data.update(pcs_extra_data)
            except Exception as e:  # Catch a broader range of exceptions
                logger.logger.error(f"Error fetching supplementary PCS power data: {e}")

    # 3. Fetch latest data for any Met Station (type 4) devices
    met_station_to_fetch_ids = [
        dev.device_id
        for dev in devices
        if dev.device_type_id == DeviceType.MET_STATION
        and dev.device_id not in all_device_extra_data
    ]
    if met_station_to_fetch_ids:
        try:
            met_station_data_values = await get_met_station_latest_values(
                device_ids=list(set(met_station_to_fetch_ids)),  # Ensure unique IDs
                project_db=project_db,
            )
            # The met_station_data_values is already in the format {device_id:
            # {poa: val, ghi: val, ...}}
            # We need to merge this carefully if a device_id could somehow
            # already be in all_device_extra_data
            # with a different structure, though for Met Stations this step is distinct.
            for dev_id, data_vals in met_station_data_values.items():
                if dev_id not in all_device_extra_data:  # Should typically be true
                    all_device_extra_data[dev_id] = data_vals
                # If it exists, assume it's from a previous step and
                # merge if necessary (unlikely for met stations)
                else:
                    if isinstance(all_device_extra_data[dev_id], dict) and isinstance(
                        data_vals, dict
                    ):
                        all_device_extra_data[dev_id].update(data_vals)
                    else:
                        all_device_extra_data[dev_id] = (
                            data_vals  # Overwrite if types are incompatible for merge
                        )
        except HTTPException as e:
            # Catch HTTP exceptions (like 404 Not Found) specifically.
            # Log as info or warning, not error, as this can be an expected state.
            if e.status_code == 404:
                logger.logger.info(
                    f"Met Station data not found (as expected): {e.detail}"
                )
            else:
                logger.logger.warning(f"HTTP error fetching Met Station data: {e}")
        except Exception as e:
            # Catch any other unexpected errors.
            logger.logger.error(
                f"An unexpected error occurred fetching Met Station data: {e}"
            )

    # --- Prepare Response ---
    # Convert devices to dicts and merge additional data if available
    response_data = []
    for device in devices:
        # Use Pydantic model for serialization using modern methods
        device_schema = interfaces.Device.model_validate(device)
        device_dict = device_schema.model_dump()

        # Get the specific extra data for this device, if any
        extra_data_for_this_device = all_device_extra_data.get(device.device_id)

        if extra_data_for_this_device:
            if device.device_type_id == DeviceType.TRACKER_ROW:
                device_dict["tracker_data"] = extra_data_for_this_device
            # Assuming PCS (2, 13) and Combiner (9) expect their data under "power_data"
            # and utility_expected returns the payload directly for these types.
            elif device.device_type_id in [
                DeviceType.PV_INVERTER,
                DeviceType.PV_DC_COMBINER,
                DeviceType.BESS_PCS,
            ]:
                device_dict["power_data"] = extra_data_for_this_device
            elif device.device_type_id == DeviceType.MET_STATION:
                # extra_data_for_this_device should be the dict like {poa: val, ...}
                device_dict["met_station_values"] = extra_data_for_this_device
            # Add other device type specific data handling here if
            # utility_expected supports them
        else:
            # Ensure keys for power_data or tracker_data are present (as None)
            # for frontend consistency if expected
            if device.device_type_id == DeviceType.TRACKER_ROW:
                device_dict["tracker_data"] = None
            elif device.device_type_id in [
                DeviceType.PV_INVERTER,
                DeviceType.PV_DC_COMBINER,
                DeviceType.BESS_PCS,
            ]:
                device_dict["power_data"] = None
            elif device.device_type_id == DeviceType.MET_STATION:
                device_dict["met_station_values"] = None
            # Met stations (type 4) etc. won't have these keys added here
            # unless explicitly handled

        response_data.append(device_dict)

    return response_data


# Removed @router.post decorator - this is now an internal helper function
async def utility_expected(
    *,
    device_ids: list[int],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project_api),
):
    """This function facilitates backend data required for GIS viewport.
        If device type is Tracker Row (29), fetches latest tracker angle.
        Otherwise, fetches actual/expected power for supported power device types.
        Accepts one or more device IDs (must be of the same supported type).
        If start/end are None for power types, fetches data for the latest hour.

    Args:
        device_ids: Description for device_ids.
        start: Description for start.
        end: Description for end.
        project_db: Description for project_db.
        project: Description for project.
    """
    # Handle optional start/end dates (only relevant for power types now)
    if start is None or end is None:
        end = pd.Timestamp.utcnow().floor("5min")
        start = end - pd.Timedelta(hours=1)

    if not device_ids:
        raise HTTPException(status_code=400, detail="No device IDs provided")

    # --- Device Type Validation ---
    # Fetch devices once for validation and later use
    project_schema = utils.get_project_schema(project_db=project_db)
    if project_schema is None:
        raise HTTPException(
            status_code=500,
            detail="Project database schema is not available.",
        )
    devices_df = await core.crud.project.devices.get_project_devices(
        device_ids=device_ids
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    devices_df = devices_df.copy()
    devices_df["device_id"] = devices_df["device_id"].astype(int)
    devices_df["device_type_id"] = devices_df["device_type_id"].astype(int)
    devices_df["parent_device_id"] = devices_df["parent_device_id"].apply(
        lambda value: None if pd.isna(value) else value
    )
    devices = list(devices_df.itertuples(index=False))
    if len(devices) != len(device_ids):
        missing_ids = set(device_ids) - set(devices_df["device_id"])
        raise HTTPException(
            status_code=404,
            detail=f"Device IDs not found: {missing_ids}",
        )

    # Store devices in a dict for easier access later
    device_dict: dict[int, typing.Any] = {
        int(typing.cast(int, dev.device_id)): dev for dev in devices
    }

    first_device_type_id = devices[0].device_type_id
    if not all(d.device_type_id == first_device_type_id for d in devices):
        raise HTTPException(
            status_code=422,
            detail="All device IDs must be of the same type.",
        )
    # --- Handle Tracker Row Case ---
    if first_device_type_id == DeviceType.TRACKER_ROW:
        sensor_type_ids = [SensorType.TRACKER_ROW_POSITION.value]

        try:
            latest_query = (
                core.crud.project.data_timeseries_last.get_data_timeseries_last(
                    device_ids=device_ids,
                    sensor_type_ids=sensor_type_ids,
                    deep=True,
                )
            )
            latest_df = await latest_query.get_async(
                output_type=OutputType.PANDAS,
                schema=project_schema,
            )

        except Exception as e:
            logger.logger.exception(
                "Tracker viewport latest query failed for device_ids=%s: %s",
                device_ids,
                e,
            )
            return {}

        if latest_df.empty:
            logger.logger.info(
                "Tracker viewport latest query returned no rows for device_ids=%s",
                device_ids,
            )
            return {}

        tracker_results: dict[int, dict[str, typing.Any]] = {}
        null_tracker_angles = 0
        for row in latest_df.itertuples(index=False):
            device_id = getattr(row, "device_id", None)
            if pd.isna(device_id):
                continue

            tracker_angle = _get_scaled_data_timeseries_last_value(row=row)
            if tracker_angle is None:
                null_tracker_angles += 1

            tracker_results[int(device_id)] = {
                "tracker_angle": tracker_angle,
                "tracker_time": _get_row_timestamp_iso(row=row),
            }

        logger.logger.info(
            "Tracker viewport mapped %s tracker rows for %s devices; null_angles=%s",
            len(tracker_results),
            len(device_ids),
            null_tracker_angles,
        )
        return tracker_results

    # --- Existing Power Logic (for non-tracker types) ---

    # --- Determine Parameters based on Device Type ---
    pv_dc_combiner_case = False
    sensor_type_ids = []  # Initialize for non-combiner case
    if first_device_type_id == DeviceType.PV_INVERTER:
        sensor_type_ids = [SensorType.PV_INVERTER_AC_POWER]
        # Add fallback expected metric IDs for PCS (expected_metric_type_id 2)
        # Try with soiling first (10), then without soiling (9), then with
        # degradation (3), then without degradation (4)
        expected_metric_ids_fallback = [10, 9, 4, 3]
        multiplier = 1_000.0  # Raw data presumed in kW?
        expected_device_ids_for_query = device_ids
    elif first_device_type_id == DeviceType.PV_DC_COMBINER:
        # Add fallback expected metric IDs for Combiner (expected_metric_type_id 1)
        # Try with soiling first (8), then without soiling (7), then with
        # degradation (1), then without degradation (2)
        expected_metric_ids_fallback = [8, 7, 2, 1]
        multiplier = 1 / 1_000  # V * A = W -> kW
        expected_device_ids_for_query = device_ids
        pv_dc_combiner_case = True
    elif first_device_type_id == DeviceType.BESS_PCS.value:  # BESS PCS
        sensor_type_ids = [SensorType.BESS_PCS_AC_POWER]  # BESS PCS AC Power
        # BESS devices don't have expected power data like PV devices
        expected_metric_ids_fallback = []
        multiplier = 1_000.0  # Raw data presumed in kW?
        expected_device_ids_for_query = device_ids
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported device type ID: {first_device_type_id}",
        )

    use_latest_power_snapshot = first_device_type_id in {
        DeviceType.PV_INVERTER,
        DeviceType.PV_DC_COMBINER,
    }
    if use_latest_power_snapshot:
        if first_device_type_id == DeviceType.PV_INVERTER:
            actual_by_device = await _get_latest_scaled_sensor_values_by_device(
                device_ids=device_ids,
                sensor_type_ids=[SensorType.PV_INVERTER_AC_POWER.value],
                project_schema=project_schema,
                multiplier=1_000.0,
            )
        else:
            actual_by_device = await _get_latest_combiner_power_by_device(
                device_ids=device_ids,
                device_dict=device_dict,
                project_schema=project_schema,
            )

        (
            expected_by_device,
            unique_versions_by_device,
        ) = await _get_latest_expected_power_by_device(
            start=start,
            end=end,
            device_ids=expected_device_ids_for_query,
            expected_metric_ids_fallback=expected_metric_ids_fallback,
            project=project,
            project_schema=project_schema,
        )

        return _build_single_point_power_results(
            device_ids=device_ids,
            actual_by_device=actual_by_device,
            expected_by_device=expected_by_device,
            unique_versions_by_device=unique_versions_by_device,
        )

    # --- Query and Calculate Actual Device Data ---
    df_actual = pd.DataFrame()  # Initialize

    if pv_dc_combiner_case:
        # --- Combiner Specific Actual Power Calculation (Optimized) ---

        # 1. Find parent PCS IDs from input combiners
        # Combiners can be children of either PCSs (type 2) or PCS Modules (type 3)
        # If parent is a module, we need to get the module's parent (the PCS)
        parent_ids = {
            device_dict[dev_id].parent_device_id
            for dev_id in device_ids
            if device_dict[dev_id].parent_device_id is not None
        }

        if not parent_ids:
            raise HTTPException(
                status_code=404,
                detail="Could not determine parent device IDs for the given combiners.",
            )

        # Fetch parent devices to check their types
        parent_device_ids = list(parent_ids)
        parent_devices_df = await core.crud.project.devices.get_project_devices(
            device_ids=[typing.cast(int, pid) for pid in parent_device_ids],
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        parent_devices_df = parent_devices_df.copy()
        parent_devices_df["device_id"] = parent_devices_df["device_id"].astype(int)
        parent_devices_df["device_type_id"] = parent_devices_df[
            "device_type_id"
        ].astype(int)
        parent_devices_df["parent_device_id"] = parent_devices_df[
            "parent_device_id"
        ].apply(lambda value: None if pd.isna(value) else value)
        parent_devices = list(parent_devices_df.itertuples(index=False))
        parent_device_dict = {
            typing.cast(int, dev.device_id): dev for dev in parent_devices
        }

        # Determine PCS IDs: if parent is a module (type 3), get its parent; if
        # it's a PCS (type 2), use it directly
        parent_pcs_ids = []
        combiner_to_parent_pcs_id = {}
        for dev_id in device_ids:
            parent_id = device_dict[dev_id].parent_device_id
            if parent_id is None:
                continue

            parent_device = parent_device_dict.get(typing.cast(int, parent_id))
            if parent_device is None:
                continue

            # If parent is a PCS Module (type 3), get its parent (the PCS)
            if parent_device.device_type_id == DeviceType.PV_INVERTER_MODULE:
                pcs_id = parent_device.parent_device_id
                if pcs_id is not None:
                    parent_pcs_ids.append(typing.cast(int, pcs_id))
                    combiner_to_parent_pcs_id[dev_id] = typing.cast(int, pcs_id)
            # If parent is already a PCS (type 2), use it directly
            elif parent_device.device_type_id == DeviceType.PV_INVERTER:
                parent_pcs_ids.append(typing.cast(int, parent_id))
                combiner_to_parent_pcs_id[dev_id] = typing.cast(int, parent_id)
            else:
                # Unexpected parent type
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Combiner {dev_id} has unexpected parent device type "
                        f"{parent_device.device_type_id}."
                    ),
                )

        # Remove duplicates from parent_pcs_ids
        parent_pcs_ids = list(set(parent_pcs_ids))

        if not parent_pcs_ids:
            raise HTTPException(
                status_code=404,
                detail="Could not determine parent PCS IDs for the given combiners.",
            )

        # DB Call 1: Fetch all relevant PV Inverter Modules using parent IDs
        all_pcs_modules_df = await core.crud.project.devices.get_project_devices(
            device_type_ids=[DeviceType.PV_INVERTER_MODULE],
            parent_device_ids=[typing.cast(int, pid) for pid in parent_pcs_ids],
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        all_pcs_modules_df = all_pcs_modules_df.copy()
        all_pcs_modules_df["device_id"] = all_pcs_modules_df["device_id"].astype(int)
        all_pcs_modules_df["parent_device_id"] = all_pcs_modules_df[
            "parent_device_id"
        ].apply(lambda value: None if pd.isna(value) else value)
        all_pcs_modules = list(all_pcs_modules_df.itertuples(index=False))
        module_ids = [typing.cast(int, mod.device_id) for mod in all_pcs_modules]

        # Build mapping from parent PCS ID to its module IDs
        parent_pcs_id_to_module_ids: dict[int, list[int]] = {}
        for mod in all_pcs_modules:
            pcs_id = mod.parent_device_id
            if pcs_id is not None:  # Ensure parent_device_id is not None
                pcs_id_int = typing.cast(int, pcs_id)
                if pcs_id_int not in parent_pcs_id_to_module_ids:
                    parent_pcs_id_to_module_ids[pcs_id_int] = []
                parent_pcs_id_to_module_ids[pcs_id_int].append(
                    typing.cast(int, mod.device_id)
                )

        if not module_ids:
            # Consider if this check is still needed if parent_pcs_id_to_module_ids
            # handles empty cases
            raise HTTPException(
                status_code=404,
                detail="Could not find PV Inverter Modules for parent PCS devices.",
            )

        # DB Call for current tags (combiners)
        tags_current_pl = await core.crud.project.tags.get_project_tags_v2(
            device_ids=device_ids,
            sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT],
        ).get_async(output_type=OutputType.POLARS, schema=project_schema)

        if tags_current_pl.is_empty():
            return {}

        tags_current_df = tags_current_pl.to_pandas()

        # DB Call for voltage tags (primary: module-level, fallback: PCS-level)
        using_pcs_level_voltage = False
        tags_voltage_pl = await core.crud.project.tags.get_project_tags_v2(
            device_ids=module_ids,
            sensor_type_ids=[SensorType.PV_INVERTER_MODULE_DC_VOLTAGE],
        ).get_async(output_type=OutputType.POLARS, schema=project_schema)

        if tags_voltage_pl.is_empty():
            tags_voltage_pl = await core.crud.project.tags.get_project_tags_v2(
                device_ids=parent_pcs_ids,  # Use PCS device IDs for fallback
                sensor_type_ids=[SensorType.PV_INVERTER_DC_VOLTAGE],
            ).get_async(output_type=OutputType.POLARS, schema=project_schema)
            using_pcs_level_voltage = True

        if tags_voltage_pl.is_empty():
            return {}

        tags_voltage_df = tags_voltage_pl.to_pandas()

        # Create maps directly from the specific tag lists
        voltage_tag_map = dict(
            zip(
                tags_voltage_df["device_id"].astype(int),
                tags_voltage_df["tag_id"].astype(int),
                strict=False,
            ),
        )
        current_tag_map = dict(
            zip(
                tags_current_df["device_id"].astype(int),
                tags_current_df["tag_id"].astype(int),
                strict=False,
            ),
        )

        # Combine tag IDs for the data query
        list(voltage_tag_map.values()) + list(
            current_tag_map.values(),
        )

        # DB Call 4: Fetch all timeseries data
        data = await DataTimeseries(
            project_name_short=project.name_short,
            filter_method=FilterMethod.TAG_POLARS,
            filter_values=pl.concat(
                [tags_voltage_pl, tags_current_pl],
                how="vertical_relaxed",
            ),
            query_start=start,
            query_end=end,
            project_db=project_db,
        ).get()

        df_data_raw = data.df.to_pandas()
        df_data_raw = df_data_raw.set_index("time")
        df_data_raw.columns = df_data_raw.columns.astype(int)

        if df_data_raw.empty:
            return {}

        # Map columns to device IDs for calculation
        # Use the maps created above
        tag_id_to_device_id_map = {v: k for k, v in voltage_tag_map.items()}
        tag_id_to_device_id_map.update({v: k for k, v in current_tag_map.items()})
        df_data = df_data_raw.rename(columns=tag_id_to_device_id_map)

        # Calculate power for each combiner
        actual_power_series_list = []
        for dev_id in device_ids:  # Use filtered list of combiners
            parent_pcs_id = combiner_to_parent_pcs_id.get(dev_id)
            if not parent_pcs_id:
                continue

            if using_pcs_level_voltage:
                # Fallback: Use the single voltage value from the parent PCS directly
                s_voltage = df_data.get(parent_pcs_id)
            else:
                # Primary: Calculate mean voltage from module-level data
                related_module_ids_for_parent = parent_pcs_id_to_module_ids.get(
                    parent_pcs_id, []
                )
                voltage_cols_present = [
                    m_id
                    for m_id in related_module_ids_for_parent
                    if m_id in df_data.columns
                ]
                if not voltage_cols_present:
                    continue
                s_voltage = df_data[voltage_cols_present].mean(axis=1)

            current_col = dev_id
            if (
                current_col not in df_data.columns
                or s_voltage is None
                or s_voltage.empty
            ):
                continue

            s_current = df_data[current_col]
            s_power_kw = s_voltage.mul(s_current) * multiplier
            s_power_kw.name = dev_id
            actual_power_series_list.append(s_power_kw)

        if not actual_power_series_list:
            return {}

        df_actual = pd.concat(actual_power_series_list, axis=1)

    else:
        # --- Standard Actual Power Fetching (Meter, PCS) ---
        tags_pl = await core.crud.project.tags.get_project_tags_v2(
            device_ids=device_ids,
            sensor_type_ids=sensor_type_ids,
        ).get_async(output_type=OutputType.POLARS, schema=project_schema)
        if tags_pl.is_empty():
            if project.project_status_type_id == ProjectStatusType.ONBOARDING.value:
                logger.logger.warning(
                    f"No suitable power tags found for device IDs {device_ids} "
                    f"with sensor types {sensor_type_ids}. "
                    f"This is normal during project onboarding "
                    "when tags are not yet configured."
                )
                return {}
            else:
                raise HTTPException(
                    status_code=404,
                    detail="No suitable power tags found for device IDs "
                    f"{device_ids} with sensor types {sensor_type_ids}.",
                )

        tags_df = tags_pl.to_pandas()

        tag_id_to_device_id = dict(
            zip(
                tags_df["tag_id"].astype(int),
                tags_df["device_id"].astype(int),
                strict=False,
            ),
        )

        data = await DataTimeseries(
            project_name_short=project.name_short,
            filter_method=FilterMethod.TAG_POLARS,
            filter_values=tags_pl,
            query_start=start,
            query_end=end,
            project_db=project_db,
        ).get()

        df_actual_raw = data.df.to_pandas()
        df_actual_raw = df_actual_raw.set_index("time")
        df_actual_raw.columns = df_actual_raw.columns.astype(int)

        if df_actual_raw.empty:
            # Return empty result or raise error? Returning empty for now.
            return {}

        # Map columns to device_id and apply multiplier
        df_actual_raw.columns = df_actual_raw.columns.map(tag_id_to_device_id)
        df_actual = df_actual_raw * multiplier

        # Ensure timezone conversion happens correctly
        df_actual.index = pd.to_datetime(df_actual.index).tz_convert(project.time_zone)

    # --- Query Expected Data with Fallbacks ---
    data_expected = None
    found_metric_id = None
    for expected_metric_id in expected_metric_ids_fallback:
        data_expected = await core.crud.project.data_expected.get_project_data_expected(
            start=start,
            end=end,
            device_ids=expected_device_ids_for_query,
            expected_metric_ids=[expected_metric_id],
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        if not data_expected.empty:
            found_metric_id = expected_metric_id
            break  # Found data, stop trying fallbacks

    if data_expected is None or data_expected.empty:
        # If no expected data, we might still return actual, or raise/return empty
        # Let's return actual data only in this case.
        df_expected_pivot = pd.DataFrame(index=df_actual.index)  # Empty DF
        df_expected_all = pd.DataFrame()  # Empty DF
    else:
        df_expected_all = data_expected.copy()
        df_expected_all["time"] = pd.to_datetime(
            df_expected_all["time"], errors="coerce"
        )
        if getattr(df_expected_all["time"].dt, "tz", None) is None:
            df_expected_all["time"] = df_expected_all["time"].dt.tz_localize(
                "UTC", nonexistent="NaT", ambiguous="NaT"
            )
        df_expected_all["time"] = df_expected_all["time"].dt.tz_convert(
            project.time_zone
        )
        # Pivot to get time index and device_id columns
        try:
            # Filter for the required metric ID *before* pivoting
            df_expected_filtered = df_expected_all[
                df_expected_all["expected_metric_id"] == found_metric_id
            ]

            if df_expected_filtered.empty:
                # Handle case where the specific metric ID isn't found
                df_expected_pivot = pd.DataFrame(index=df_actual.index)  # Empty DF
                df_expected_all = (
                    pd.DataFrame()
                )  # Ensure this is also empty for later logic
            else:
                # Pivot the *filtered* DataFrame
                df_expected_pivot = df_expected_filtered.pivot(
                    index="time",
                    columns="device_id",
                    values="value",
                )
                # Reindex expected to match actual timestamps and handle timezone
                df_expected_pivot = df_expected_pivot.reindex(
                    df_actual.index,
                    method="nearest",
                    limit=1,
                )  # Use nearest neighbor fill
                df_expected_pivot.index = pd.to_datetime(
                    df_expected_pivot.index,
                ).tz_convert(project.time_zone)
                df_expected_pivot = df_expected_pivot / 1_000  # Convert from W to kW
        except Exception as e:
            # Handle potential pivot errors (e.g., duplicate index/column entries)
            # Log the error? For now, create empty DF
            logger.logger.error(f"Error pivoting expected data: {e}")  # Basic logging
            df_expected_pivot = pd.DataFrame(index=df_actual.index)
            df_expected_all = pd.DataFrame()  # Ensure it's empty if pivot fails

    # --- Structure Output ---
    results: dict[int, dict[str, typing.Any]] = {}
    # Convert index to ISO format strings for JSON serialization
    times_list_iso = [ts.isoformat() for ts in df_actual.index]

    # Determine which expected column to use based on device type
    expected_col_key = expected_device_ids_for_query[
        0
    ]  # e.g., 1 for Meter, or first PCS id

    for dev_id in device_ids:
        actual_power_series = df_actual.get(
            dev_id,
            pd.Series(index=df_actual.index, dtype=float),
        )  # Handle missing actual data column

        # Get expected data (use the determined column key)
        expected_power_series = df_expected_pivot.get(
            dev_id,
            pd.Series(index=df_actual.index, dtype=float),
        )

        # Get unique versions for the expected device id column
        unique_versions = []
        if (
            not df_expected_all.empty
            and "device_id" in df_expected_all.columns
            and expected_col_key in df_expected_all["device_id"].values
        ):
            unique_versions = sorted(
                df_expected_all[df_expected_all["device_id"] == expected_col_key][
                    "version"
                ]
                .dropna()
                .unique()
                .tolist(),
            )

        results[dev_id] = {
            "times": times_list_iso,
            "actual": {
                "power": [
                    float(value) if pd.notna(value) else None
                    for value in actual_power_series.tolist()
                ],
            },  # Convert NaN to None for JSON
            "expected_soiled": {
                "power": [
                    float(value) if pd.notna(value) else None
                    for value in expected_power_series.tolist()
                ],
                "unique_versions": unique_versions,
            },
        }

    return results


async def get_met_station_latest_values(
    *,
    device_ids: list[int],
    project_db: Session,
) -> dict[int, dict[str, float]]:
    """Fetches the latest sensor values (POA, GHI, Ambient Temp, Wind Speed)
        for the given Met Station device IDs.

    Args:
        device_ids: Description for device_ids.
        project_db: Description for project_db.
    """
    if not device_ids:
        return {}

    met_sensor_type_to_field = {
        SensorType.MET_STATION_POA.value: "poa",
        SensorType.MET_STATION_GHI.value: "ghi",
        SensorType.MET_STATION_AMBIENT_TEMPERATURE.value: "ambient_temp",
        SensorType.MET_STATION_WIND_SPEED.value: "wind_speed",
    }
    project_schema = utils.get_project_schema(project_db=project_db)

    try:
        latest_query = core.crud.project.data_timeseries_last.get_data_timeseries_last(
            device_ids=device_ids,
            sensor_type_ids=list(met_sensor_type_to_field),
            deep=True,
        )
        latest_df = await latest_query.get_async(
            output_type=OutputType.POLARS,
            schema=project_schema,
        )
        if latest_df.is_empty():
            logger.logger.info(
                f"No relevant Met Station tags found for devices: {device_ids}"
            )
            return {}

        latest_values: dict[int, dict[str, float]] = {}
        for row in latest_df.to_dicts():
            device_id = row.get("device_id")
            sensor_type_id = row.get("sensor_type_id")
            if pd.isna(device_id) or pd.isna(sensor_type_id):
                continue

            field_name = met_sensor_type_to_field.get(int(sensor_type_id))
            if field_name is None:
                continue

            value = _get_scaled_data_timeseries_last_value(row=row)
            if value is None:
                continue

            latest_values.setdefault(int(device_id), {})[field_name] = value

        # Return the dictionary directly, FastAPI will handle JSON serialization
        return latest_values

    except HTTPException as e:
        if e.status_code == 404:
            logger.logger.info(
                f"No data found for Met Station devices {device_ids}: {e.detail}"
            )
        else:
            logger.logger.error(
                "HTTP error while fetching Met Station data for devices "
                f"{device_ids}: {e}"
            )
        return {}
    except Exception as e:
        logger.logger.error(
            "An unexpected error occurred while fetching Met Station data for "
            f"devices {device_ids}: {e}"
        )
        return {}
