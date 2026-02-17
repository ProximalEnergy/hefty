"""
BESS (Battery Energy Storage System) domain logic.

This module contains pure business logic functions for BESS calculations
that are independent of any external technologies or frameworks.
"""

from typing import Optional

import numpy as np
import xarray as xr

from kpi_pipeline.base.enums import Aggregation
from kpi_pipeline.base.protocols import CoordCombinerProtocol
from kpi_pipeline.domain.general import diff, filter_by_capacity


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


def max_run_sm_1d(a: np.ndarray) -> float:
    """
    It's assumed that all values are non-negative
    """
    if np.isnan(a).all():
        return np.nan

    best = 0
    current = 0

    for v in a:
        if np.isnan(v) or v <= 0:
            current = 0
        else:
            current += v
            if current > best:
                best = current
    return best


def maximum_continuous_discharge(
    *,
    energy_discharged_kwh: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
    energy_capacity_kwh: Optional[xr.DataArray] = None,
) -> xr.DataArray:
    discharge_only = energy_discharged_kwh.where(energy_discharged_kwh > 0)
    grouped = time_combiner.group(discharge_only)
    time_dim = time_combiner.get_high_res_time_axis().value

    def reducer(g: xr.DataArray) -> xr.DataArray:
        return xr.apply_ufunc(  # type: ignore
            max_run_sm_1d,
            g,
            input_core_dims=[[time_dim]],
            output_core_dims=[()],
        )

    result = grouped.map(reducer)

    return filter_by_capacity(data=result, capacity=energy_capacity_kwh)


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
