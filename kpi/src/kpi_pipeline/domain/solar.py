"""
Solar domain logic.

This module contains pure business logic functions for solar calculations
that are independent of any external technologies or frameworks.
"""

import numpy as np
import xarray as xr

from kpi_pipeline.base.enums import Aggregation, DeviceType, Time
from kpi_pipeline.base.protocols import CoordCombinerProtocol
from kpi_pipeline.domain.general import all_not_null_mask
from kpi_pipeline.infra.utils import (
    to_local,
)

# Solar reference constants
REFERENCE_IRRADIANCE = 1000  # W/m²


def performance_ratio(
    *,
    energy: xr.DataArray,
    power_capacity: xr.DataArray,
    insolation_poa: xr.DataArray,
    combiner: CoordCombinerProtocol,
    reference_irradiance: float = REFERENCE_IRRADIANCE,
) -> xr.DataArray:
    """
    Calculate the daily performance ratio for a solar power system.

    Performance ratio is a key metric that indicates how efficiently a solar
    system converts available solar irradiance into electrical energy,
    accounting for all system losses.

    Args:
        energy_project: 5-minute energy production data
        power_capacity_dc_project: DC power capacity of the project
        insolation_poa_project: 5-minute plane-of-array irradiance data
        time_zone: Time zone for daily aggregation
        reference_irradiance: Reference irradiance for normalization (default: 1000 W/m²)

    Returns:
        Daily performance ratio as a dimensionless ratio (0.0 to 1.0+)
    """
    mask = all_not_null_mask(energy, insolation_poa)
    concurrent_energy = energy.where(mask)
    concurrent_insolation_poa = insolation_poa.where(mask)
    energy_sum = combiner.agg(concurrent_energy, agg=Aggregation.SUM)
    insolation_sum = combiner.agg(concurrent_insolation_poa, agg=Aggregation.SUM)
    specific_yield = energy_sum / power_capacity
    return specific_yield / (insolation_sum / reference_irradiance)


def filter_to_solar_noon[T: xr.DataArray | xr.Dataset](
    x: T, time_zone: str, drop: bool = False
) -> T:
    local_pandas_index = to_local(
        x.coords[Time.TIME_5MIN_UTC.value].to_numpy(), time_zone
    )
    arr = (local_pandas_index.hour == 12) & (local_pandas_index.minute < 30) | (
        local_pandas_index.hour == 11
    ) & (local_pandas_index.minute >= 30)
    x_arr = xr.DataArray(
        arr, coords={Time.TIME_5MIN_UTC.value: x.coords[Time.TIME_5MIN_UTC.value]}
    )
    return x.where(x_arr, drop=drop)  # type: ignore


def dc_field_health(
    *,
    current_combiner: xr.DataArray,
    power_capacity_dc_combiner: xr.DataArray,
    time_zone: str,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    current_during_solar_noon = filter_to_solar_noon(
        current_combiner, time_zone, drop=True
    )
    current_during_solar_noon_not_null = current_during_solar_noon.ffill(
        dim=Time.TIME_5MIN_UTC.value
    )
    first_normalization = (
        current_during_solar_noon_not_null / power_capacity_dc_combiner
    )
    percentile_99 = first_normalization.quantile(
        q=0.99, dim=DeviceType.PV_DC_COMBINER.name.lower()
    ).drop("quantile")  # type: ignore
    second_normalization = first_normalization / percentile_99
    return time_combiner.agg(second_normalization, agg=Aggregation.MEAN)


def project_mean_irradiance_poa_w_m2(
    *,
    met_station_irradiance_poa_w_m2: xr.DataArray,
    device_type: DeviceType = DeviceType.MET_STATION,
    irradiance_poa_minimum_w_m2: float = 10,
) -> xr.DataArray:
    return (
        met_station_irradiance_poa_w_m2.where(
            met_station_irradiance_poa_w_m2 > irradiance_poa_minimum_w_m2
        )
        .mean(dim=device_type.name.lower())
        .fillna(0)
    )


def mechanical_availability(
    *,
    power_kw: xr.DataArray,
    met_station_poa_irradiance_w_m2: xr.DataArray,
    poa_threshold: float = 90,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    irradiance_project_w_m2 = project_mean_irradiance_poa_w_m2(
        met_station_irradiance_poa_w_m2=met_station_poa_irradiance_w_m2,
    )
    power_filtered = power_kw.where(irradiance_project_w_m2 > poa_threshold)
    is_available = xr.where(
        power_filtered > 0, 1.0, xr.where(power_filtered <= 0, 0.0, np.nan)
    )
    return time_combiner.agg(is_available, agg=Aggregation.MEAN)


def combiner_mechanical_availability(
    *,
    pcs_power_kw: xr.DataArray,
    combiner_to_pcs_combiner: CoordCombinerProtocol,
    combiner_current_amps: xr.DataArray,
    met_station_poa_irradiance_w_m2: xr.DataArray,
    combiner_current_threshold_amps: float = 10,
    irradiance_poa_threshold_w_m2: float = 90,
    pcs_power_threshold_kw: float = 5,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    power_expanded = combiner_to_pcs_combiner.broadcast(
        x=pcs_power_kw,
    )

    project_poa_irradiance_w_m2 = project_mean_irradiance_poa_w_m2(
        met_station_irradiance_poa_w_m2=met_station_poa_irradiance_w_m2,
    )

    is_valid = (project_poa_irradiance_w_m2 > irradiance_poa_threshold_w_m2) & (
        power_expanded > pcs_power_threshold_kw
    )
    is_available = (combiner_current_amps > combiner_current_threshold_amps) & is_valid

    # set to 1.0 if the combiner is available, 0.0 if the combiner is not available during a valid period
    # and nan otherwise
    available_numeric = xr.where(is_available, 1.0, xr.where(is_valid, 0.0, np.nan))
    return time_combiner.agg(available_numeric, agg=Aggregation.MEAN)


def tracker_deviation_from_setpoint(
    *,
    position: xr.DataArray,
    setpoint: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    diff = xr.DataArray(abs(position - setpoint))
    return time_combiner.agg(diff, agg=Aggregation.MEAN)


def tracker_setpoint_deviation_from_median(
    *, setpoint: xr.DataArray, time_combiner: CoordCombinerProtocol
) -> xr.DataArray:
    median = setpoint.median(dim=DeviceType.TRACKER_ROW.name.lower())
    diff = xr.DataArray(abs(setpoint - median))
    return time_combiner.agg(diff, agg=Aggregation.MEAN)


def tracker_availability(
    *,
    position: xr.DataArray,
    setpoint: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
    threshold_deg: float = 2.0,
) -> xr.DataArray:
    diff = abs(position - setpoint)
    # set to 1.0 if the difference between position and setpoint is less than or equal to threshold_deg
    # set to 0.0 if the difference between position and setpoint is greater than threshold_deg
    # everything else is left as nan which is what we want
    tracker_available = xr.where(
        diff <= threshold_deg, 1.0, xr.where(diff > threshold_deg, 0.0, np.nan)
    )

    return time_combiner.agg(tracker_available, agg=Aggregation.MEAN)


def performance_index(
    *,
    expected_energy: xr.DataArray,
    actual_energy: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    non_null_mask = all_not_null_mask(expected_energy, actual_energy)
    concurrent_expected_energy = expected_energy.where(non_null_mask)
    concurrent_actual_energy = actual_energy.where(non_null_mask)
    expected_energy_sum = time_combiner.agg(
        concurrent_expected_energy,
        agg=Aggregation.SUM,
    )
    actual_energy_sum = time_combiner.agg(
        concurrent_actual_energy,
        agg=Aggregation.SUM,
    )
    return actual_energy_sum / expected_energy_sum


def curtailed_power_from_eem(
    *,
    power_setpoint: xr.DataArray,
    power_actual: xr.DataArray,
    power_expected: xr.DataArray,
    threshold: float = 0.98,
) -> xr.DataArray:
    non_null_mask = all_not_null_mask(power_setpoint, power_actual, power_expected)
    concurrent_power_setpoint = power_setpoint.where(non_null_mask)
    concurrent_power_actual = power_actual.where(non_null_mask)
    concurrent_power_expected = power_expected.where(non_null_mask)

    during_curtailment = concurrent_power_actual > threshold * concurrent_power_setpoint
    curtailed_power = concurrent_power_expected.where(
        during_curtailment
    ) - concurrent_power_actual.where(during_curtailment)
    curtailed_power[curtailed_power < 0] = 0

    return curtailed_power
