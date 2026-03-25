"""
BESS (Battery Energy Storage System) domain logic.

This module contains pure business logic functions for BESS calculations
that are independent of any external technologies or frameworks.
"""

import numpy as np
import xarray as xr
from kpi_pipeline.base.enums import Aggregation, Time
from kpi_pipeline.base.protocols import CoordCombinerProtocol
from kpi_pipeline.domain.general import cumsum, diff, filter_by_capacity


def resting_soc(*, x: xr.DataArray, threshold: float = 0.01) -> xr.DataArray:
    """
    Identify resting state-of-charge periods in battery data.

    This function identifies periods when the battery's state of charge (SOC)
    is relatively stable, indicating the battery is at rest (not actively
    charging or discharging).

    Args:
        x: State of charge data array
        threshold: Maximum allowed change rate to consider as "resting" (default: 0.01)

    Returns:
        SOC values during resting periods, with non-resting periods set to NaN
    """
    diff_ = abs(diff(x))
    return x.where(diff_ < threshold)


def daily_average_c_rate(
    *,
    daily_energy_charged: xr.DataArray,
    daily_energy_discharged: xr.DataArray,
    energy_capacity: xr.DataArray,
) -> xr.DataArray:
    average_abs_power = (daily_energy_charged + daily_energy_discharged) / 24
    return average_abs_power / energy_capacity


def daily_average_c_rate_charging(
    *,
    daily_energy_charged: xr.DataArray,
    energy_capacity: xr.DataArray,
) -> xr.DataArray:
    average_power_while_charging = daily_energy_charged / 24
    return average_power_while_charging / energy_capacity


def is_charging(*, x: xr.DataArray, threshold: float = 0.01) -> xr.DataArray:
    return x < -threshold


def is_discharging(*, x: xr.DataArray, threshold: float = 0.01) -> xr.DataArray:
    return x > threshold


def is_idling(*, x: xr.DataArray, threshold: float = 0.01) -> xr.DataArray:
    return xr.DataArray(abs(x) < threshold)


def average_while_charging(
    *,
    x: xr.DataArray,
    c_rate: xr.DataArray,
    combiner: CoordCombinerProtocol,
    threshold: float = -0.01,
) -> xr.DataArray:
    filtered = x.where(is_charging(x=c_rate, threshold=threshold))
    return combiner.agg(filtered, agg=Aggregation.MEAN)


def average_while_discharging(
    *,
    x: xr.DataArray,
    c_rate: xr.DataArray,
    combiner: CoordCombinerProtocol,
    threshold: float = 0.01,
) -> xr.DataArray:
    filtered = x.where(is_discharging(x=c_rate, threshold=threshold))
    return combiner.agg(filtered, agg=Aggregation.MEAN)


def cycle_count_from_soc(
    *,
    soc_5m: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    cycle_abs = xr.DataArray(abs(diff(soc_5m)) / 2)
    return time_combiner.agg(cycle_abs, agg=Aggregation.SUM)


def charging_cycles_from_soc(
    *,
    soc_5m: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    cycle_abs = diff(soc_5m)
    charging_periods = cycle_abs.where(cycle_abs >= 0)
    return time_combiner.agg(charging_periods, agg=Aggregation.SUM)


def discharging_cycles_from_soc(
    *,
    soc_5m: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    cycle_abs = diff(soc_5m)
    discharging_periods = -cycle_abs.where(cycle_abs <= 0)
    return time_combiner.agg(discharging_periods, agg=Aggregation.SUM)


def maximum_continuous_discharge(
    *,
    energy_discharged_kwh_5m: xr.DataArray,
    energy_charged_kwh_5m: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
    energy_capacity_kwh: xr.DataArray | None = None,
) -> xr.DataArray:
    """
    Calculates the total energy discharged during a single continuous period.
    Any interval where there is any charging (even if there is both charging
    and discharging) is ignored. If multiple continuous periods of discharging
    exist, the maximum is returned.

    If a period of discharging straddles midnight, it is counted as a discharge
    period for the following day.

    Validation is performed to make sure that the total energy discharged
    is not greater than the energy capacity.
    """
    EPSILON = 1e-6

    total_energy_discharged_kwh_5m = cumsum(
        energy_discharged_kwh_5m, time_dim=Time.TIME_5MIN_UTC
    )

    total_discharged_while_charging = total_energy_discharged_kwh_5m.where(
        energy_charged_kwh_5m > EPSILON
    )

    # determine a baseline total from the most recent charging event
    total_discharged_since_last_charging = total_discharged_while_charging.ffill(
        dim=Time.TIME_5MIN_UTC.value
    ).fillna(total_energy_discharged_kwh_5m.min())

    total_discharged_during_discharging_event = (
        total_energy_discharged_kwh_5m - total_discharged_since_last_charging
    )

    # make sure the total discharged is not greater than the energy capacity
    filtered = filter_by_capacity(
        data=total_discharged_during_discharging_event,
        capacity=energy_capacity_kwh,
    )

    return time_combiner.agg(filtered, agg=Aggregation.MAX)


def bess_string_complete_availability(
    *,
    bess_string_status: xr.DataArray,
    bess_bank_status: xr.DataArray,
    string_to_bank_combiner: CoordCombinerProtocol,
    bess_pcs_status: xr.DataArray,
    string_to_pcs_combiner: CoordCombinerProtocol,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    bank_status_expanded = string_to_bank_combiner.broadcast(
        x=bess_bank_status,
    )
    pcs_status_expanded = string_to_pcs_combiner.broadcast(
        x=bess_pcs_status,
    )
    overall_status = bess_string_status | bank_status_expanded | pcs_status_expanded
    return time_combiner.agg(1 - overall_status, agg=Aggregation.MEAN)


def squeeze_fill_energy_accumulator(
    *,
    total_energy_5m: xr.DataArray,
    power_capacity_kw: xr.DataArray,
    max_step_ratio: float = 1.0,
) -> xr.DataArray:
    """
    If the jump in energy accumulation is small, just forward fill the
    gaps, but if it's large, leave it blank.
    In this implementation, if there is an open gap at the end, it is forward filled,
    and if there is an open gap at the beginning, it is backward filled.
    total_energy_5m is expected to be increasing monotonically.
    """
    # This function is not used yet, but will be used on energy accumulators
    energy_ffill = total_energy_5m.ffill(dim=Time.TIME_5MIN_UTC.value)
    energy_bfill = total_energy_5m.bfill(dim=Time.TIME_5MIN_UTC.value)

    # theoretically the maximum jump in 5 minutes
    # is 1/12th of the power capacity (12 steps per hour)
    max_step_energy = max_step_ratio * power_capacity_kw / 12

    energy_diff = energy_ffill - energy_bfill

    return energy_ffill.where(np.abs(energy_diff) <= max_step_energy)


def reconstruct_accumulator(
    *,
    total_energy_kw_5m: xr.DataArray,
    modulus: float,
    max_positive_step: float | None = None,
) -> xr.DataArray:
    """
    Turns a cycling accumulation into an increasing monotonic function.
    Importantly, jumps from high value that roll over the the low value
    are captured properly rather than just assuming they are zero.
    If max_positive_step is provided, any positive jumps greater than
    max_positive_step are set to zero.
    """
    bfilled = total_energy_kw_5m.bfill(dim=Time.TIME_5MIN_UTC.value)
    max_negative_step = 1e-6
    difference = (
        (diff(bfilled, time_dim=Time.TIME_5MIN_UTC) + max_negative_step) % modulus
    ) - max_negative_step
    if max_positive_step is not None:
        difference = difference.where(difference < max_positive_step)
    return cumsum(difference, time_dim=Time.TIME_5MIN_UTC)


def event_change_to_in_event(*, x: xr.DataArray) -> xr.DataArray:
    return x.cumsum(dim=Time.TIME_5MIN_UTC.value) > 0


def energy_efficiency(
    *,
    energy_source_kwh: xr.DataArray,
    energy_sink_kwh: xr.DataArray,
    energy_capacity_kwh: xr.DataArray,
    min_source_energy_capacity_factor: float = 0.0,
    max_efficiency: float = 1.0,
) -> xr.DataArray:
    source_filtered = energy_source_kwh.where(
        energy_source_kwh > min_source_energy_capacity_factor * energy_capacity_kwh
    )
    efficiency = energy_sink_kwh / source_filtered
    return efficiency.where(efficiency <= max_efficiency)


def variance(
    *, x: xr.DataArray, combiner: CoordCombinerProtocol, min_data_coverage: float = 0.5
) -> xr.DataArray:
    data_coverage = combiner.agg(x.notnull(), agg=Aggregation.MEAN)
    var = combiner.group(x).var(dim=combiner.dim())
    return var.where(data_coverage >= min_data_coverage)


def soc_balance_score(*, soc_variance: xr.DataArray) -> xr.DataArray:
    sqr: xr.DataArray = np.sqrt(soc_variance)  # type: ignore
    return 1 - 2 * sqr
