import numpy as np
import pandas as pd
import xarray as xr
from core.enumerations import DeviceTypeEnum

from kpi.base.enumeration import TimeCoord
from kpi.base.util import coord
from kpi.domain.agg.across_devices import mean_across_devices
from kpi.domain.agg.resample import resample_diff, resample_sum
from kpi.domain.general import filter_energy_5m
from kpi.domain.pv import theoretical_poa_irradiance
from kpi.domain.util import diff, fill_na_with_arrays
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import (
    DeviceTypeConstant,
    TimeCoordArg,
    TimeZone,
    grouper,
    optional,
    required,
)
from kpi.op.transform.method import MethodCalc, calc_field
from kpi.registry.download.device.pv.hierarchy import DownloadDevicePvHierarchy
from kpi.registry.download.expected_energy import DownloadExpectedEnergy as Expected
from kpi.registry.download.sensor.pv import DownloadSensorPv
from kpi.registry.transform.hybrid.api import date_local_5m
from kpi.registry.transform.pv.clean import TransformPvClean as Clean


def time_local_5m(time_5m_utc: pd.DatetimeIndex, time_zone: str) -> xr.DataArray:
    """Convert 5-minute UTC timestamps to local wall time.

    Args:
        time_5m_utc: UTC 5-minute index from the dataset.
        time_zone: IANA timezone name for the project.

    Returns:
        Local datetime values on the 5-minute UTC coordinate grid.
    """
    local_time = time_5m_utc.tz_convert(time_zone).tz_localize(None)
    return xr.DataArray(
        local_time.values,
        dims=[TimeCoord.TIME_5MIN_UTC.value],
        coords={TimeCoord.TIME_5MIN_UTC.value: time_5m_utc.values},
    )


def project_insolation_d(
    *, irradiance: xr.DataArray, date_local_5m: xr.DataArray
) -> xr.DataArray:
    """Daily plane-of-array insolation from 5-minute irradiance.

    Args:
        irradiance: POA irradiance at 5-minute resolution.
        date_local_5m: Local date grouper aligned to the time dimension.

    Returns:
        Daily insolation (irradiance sum / 12).
    """
    return resample_sum(irradiance, grouper=date_local_5m) / 12


def inverter_mechanical_availability_5m(
    *, power: xr.DataArray, met_poa: xr.DataArray
) -> xr.DataArray:
    """PCS mechanical availability from power during high-irradiance periods.

    Args:
        power: Inverter AC power at 5-minute resolution.
        met_poa: Met-station POA irradiance at 5-minute resolution.

    Returns:
        ``1.0`` when filtered power is positive, ``0.0`` when zero, else NaN.
    """
    minimum_irradiance = 10
    poa_threshold = 90
    epsilon = 1e-06
    project_mean_irradiance = met_poa.where(met_poa >= minimum_irradiance).mean(
        dim=coord(DeviceTypeEnum.MET_STATION)
    )
    power_filtered = power.where(project_mean_irradiance > poa_threshold)
    return xr.where(
        power_filtered > epsilon, 1.0, xr.where(power_filtered < epsilon, 0.0, np.nan)
    )


def combiner_mechanical_availability_5m(
    *,
    pcs_power: xr.DataArray,
    combiner_current: xr.DataArray,
    combiner_to_inverter: xr.DataArray,
    met_poa: xr.DataArray,
) -> xr.DataArray:
    """Combiner mechanical availability during high-irradiance PCS production.

    Args:
        pcs_power: Inverter AC power at 5-minute resolution.
        combiner_current: Combiner current at 5-minute resolution.
        combiner_to_inverter: Combiner-to-inverter device mapping.
        met_poa: Met-station POA irradiance at 5-minute resolution.

    Returns:
        ``1.0`` when available, ``0.0`` when valid but unavailable, else NaN.
    """
    minimum_irradiance = 10
    poa_threshold = 90
    current_threshold_amps = 10
    pcs_power_threshold = 5
    project_mean_irradiance = met_poa.where(met_poa >= minimum_irradiance).mean(
        dim=coord(DeviceTypeEnum.MET_STATION)
    )
    power_broadcasted = pcs_power.sel(
        {coord(DeviceTypeEnum.PV_INVERTER): combiner_to_inverter}
    ).drop_vars(coord(DeviceTypeEnum.PV_INVERTER))
    is_valid = (project_mean_irradiance > poa_threshold) & (
        power_broadcasted > pcs_power_threshold
    )
    is_available = (combiner_current > current_threshold_amps) & is_valid
    return xr.where(is_available, 1.0, xr.where(is_valid, 0.0, np.nan))


def tracker_row_deviation_from_setpoint_deg_5m(
    *, position: xr.DataArray, setpoint: xr.DataArray
) -> xr.DataArray:
    """Absolute tracker position deviation from setpoint.

    Args:
        position: Tracker row position in degrees.
        setpoint: Tracker row setpoint in degrees.

    Returns:
        ``|position - setpoint|``.
    """
    return abs(position - setpoint)


def tracker_row_is_available_5m(
    *, position: xr.DataArray, setpoint: xr.DataArray, threshold_deg: float = 2
) -> xr.DataArray:
    """Tracker row availability from position vs setpoint.

    Args:
        position: Tracker row position in degrees.
        setpoint: Tracker row setpoint in degrees.
        threshold_deg: Maximum deviation treated as available.

    Returns:
        ``1.0`` within threshold, ``0.0`` beyond, else NaN.
    """
    difference = tracker_row_deviation_from_setpoint_deg_5m(
        position=position, setpoint=setpoint
    )
    return xr.where(
        difference <= threshold_deg,
        1.0,
        xr.where(difference > threshold_deg, 0.0, np.nan),
    )


def tracker_row_setpoint_deviation_from_median_deg_5m(
    setpoint: xr.DataArray,
) -> xr.DataArray:
    """Absolute deviation of tracker setpoint from row median setpoint.

    Args:
        setpoint: Tracker row setpoint in degrees.

    Returns:
        ``|setpoint - median(setpoint)|`` across tracker rows.
    """
    return abs(setpoint - setpoint.median(dim=coord(DeviceTypeEnum.TRACKER_ROW)))


class TransformPvEvaluate(FieldRegistry[MethodCalc]):
    project_energy_exported_to_grid_unfiltered_kwh_5m = calc_field(diff)(
        required(Clean.project_total_energy_exported_to_grid_filled_kwh_5m)
    )

    project_energy_exported_to_grid_kwh_5m = calc_field(filter_energy_5m)(
        energy_unfiltered_5m=required(
            project_energy_exported_to_grid_unfiltered_kwh_5m
        ),
        power_capacity=required(Clean.project_ac_power_capacity_kw),
    )

    project_energy_production_unfiltered_kwh_d = calc_field(resample_diff)(
        required(Clean.project_total_energy_exported_to_grid_filled_kwh_5m),
        grouper=grouper(date_local_5m),
    )

    inverter_energy_production_unfiltered_kwh_d = calc_field(resample_diff)(
        required(Clean.inverter_total_energy_production_filled_kwh_5m),
        grouper=grouper(date_local_5m),
    )

    project_expected_energy_best_kwh_5m = calc_field(fill_na_with_arrays)(
        optional(Expected.project_expected_energy_degraded_soiled_kwh_5m),
        optional(Expected.project_expected_energy_degraded_kwh_5m),
        optional(Expected.project_expected_energy_soiled_kwh_5m),
        optional(Expected.project_expected_energy_kwh_5m),
    )

    combiner_expected_energy_best_kwh_5m = calc_field(fill_na_with_arrays)(
        optional(Expected.combiner_expected_energy_degraded_soiled_kwh_5m),
        optional(Expected.combiner_expected_energy_degraded_kwh_5m),
        optional(Expected.combiner_expected_energy_soiled_kwh_5m),
        optional(Expected.combiner_expected_energy_kwh_5m),
    )

    project_poa_irradiance_w_m2_5m = calc_field(mean_across_devices)(
        required(Clean.met_poa_irradiance_w_m2_5m),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.MET_STATION),
    )

    project_insolation_d = calc_field(project_insolation_d)(
        irradiance=required(project_poa_irradiance_w_m2_5m),
        date_local_5m=grouper(date_local_5m),
    )

    inverter_mechanical_availability_5m = calc_field(
        inverter_mechanical_availability_5m
    )(
        power=required(Clean.inverter_ac_power_kw_5m),
        met_poa=required(Clean.met_poa_irradiance_w_m2_5m),
    )

    combiner_mechanical_availability_5m = calc_field(
        combiner_mechanical_availability_5m
    )(
        pcs_power=required(Clean.inverter_ac_power_kw_5m),
        combiner_current=required(DownloadSensorPv.combiner_current_raw_amps_5m),
        combiner_to_inverter=required(DownloadDevicePvHierarchy.combiner_to_inverter),
        met_poa=required(Clean.met_poa_irradiance_w_m2_5m),
    )

    tracker_row_is_available_5m = calc_field(tracker_row_is_available_5m)(
        position=required(Clean.tracker_row_position_deg_5m),
        setpoint=required(Clean.tracker_row_setpoint_deg_5m),
    )

    project_theoretical_poa_irradiance_w_m2_5m = calc_field(theoretical_poa_irradiance)(
        time_utc=TimeCoordArg(time_coord=TimeCoord.TIME_5MIN_UTC),
        latitude=required(Clean.project_latitude_deg),
        longitude=required(Clean.project_longitude_deg),
        altitude_m=optional(Clean.project_elevation_m),
        time_zone=TimeZone(),
    )

    tracker_row_deviation_from_setpoint_deg_5m = calc_field(
        tracker_row_deviation_from_setpoint_deg_5m
    )(
        position=required(Clean.tracker_row_position_deg_5m),
        setpoint=required(Clean.tracker_row_setpoint_deg_5m),
    )

    tracker_row_setpoint_deviation_from_median_deg_5m = calc_field(
        tracker_row_setpoint_deviation_from_median_deg_5m
    )(setpoint=required(Clean.tracker_row_setpoint_deg_5m))
