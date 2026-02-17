"""
General domain logic.

This module contains general-purpose business logic functions that can be used
across different domains (BESS, Solar, etc.) and are independent of any
external technologies or frameworks.
"""

import functools
import operator
from typing import Optional

import numpy as np
import xarray as xr

from kpi_pipeline.base.enums import Aggregation, Time
from kpi_pipeline.base.protocols import CoordCombinerProtocol
from kpi_pipeline.infra.exceptions import ValidationError
from kpi_pipeline.infra.utils import calculate_seconds


def weighted_average(
    *, array: xr.DataArray, weights: xr.DataArray, min_count: int = 1
) -> xr.DataArray:
    """
    Calculate weighted average of an array using provided weights.

    This function computes the weighted average by multiplying the array values
    by their corresponding weights, then dividing by the sum of weights.
    Only non-null products are considered in the calculation.

    Args:
        array: Input data array to average
        weights: Weight values for each element
        min_count: Minimum number of non-null values required (default: 1)

    Returns:
        Weighted average array with weights dimension(s) reduced
    """
    product = array * weights
    product_is_not_null = ~product.isnull()
    non_null_weights = weights.where(product_is_not_null)
    return product.sum(dim=weights.dims, min_count=min_count) / non_null_weights.sum(
        dim=weights.dims, min_count=min_count
    )


def filter_by_capacity(
    *,
    data: xr.DataArray,
    capacity: Optional[xr.DataArray] = None,
    min_capacity_factor: float = 0.0,
    max_capacity_factor: float = 1.0,
) -> xr.DataArray:
    """
    Filter data based on capacity factor bounds.

    This function filters data values to only include those within specified
    capacity factor ranges. Capacity factor is the ratio of actual output
    to maximum possible output.

    Args:
        data: Input data array to filter
        capacity: Capacity reference values
        min_capacity_factor: Minimum capacity factor (default: 0.0)
        max_capacity_factor: Maximum capacity factor (default: 1.0)

    Returns:
        Filtered data array with values outside capacity bounds set to NaN
    """
    if capacity is None:
        return data
    return data.where(
        (data >= min_capacity_factor * capacity)
        & (data <= max_capacity_factor * capacity)
    )


def verify_by_capacity(
    *,
    data: xr.DataArray,
    capacity: Optional[xr.DataArray] = None,
    min_capacity_factor: float = 0.0,
    max_capacity_factor: float = 1.0,
) -> xr.DataArray:
    if capacity is None:
        return data
    minimum = (data / capacity).min()
    if minimum < min_capacity_factor:
        raise ValidationError(
            f"normalized value {minimum} is less than minimum capacity factor {min_capacity_factor}"
        )
    maximum = (data / capacity).max()
    if maximum > max_capacity_factor:
        raise ValidationError(
            f"normalized value {maximum} is greater than maximum capacity factor {max_capacity_factor}"
        )
    return data


def accumulator_differences(
    *,
    x: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
) -> xr.DataArray:
    high_res_time_axis = time_combiner.get_high_res_time_axis().value
    fill_nas = x.ffill(dim=high_res_time_axis).bfill(dim=high_res_time_axis)
    firsts = time_combiner.group(fill_nas).first()
    return diff(firsts, time_dim=time_combiner.get_low_res_time_axis())


def accumulate_energy_then_verify_by_capacity(
    *,
    data: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
    capacity: Optional[xr.DataArray] = None,
    min_capacity_factor: float = 0.0,
    max_capacity_factor: float = 1.0,
) -> xr.DataArray:
    x = accumulator_differences(x=data, time_combiner=time_combiner)
    return verify_by_capacity(
        data=x,
        capacity=capacity,
        min_capacity_factor=min_capacity_factor,
        max_capacity_factor=max_capacity_factor,
    )


def accumulate_energy_then_filter_by_capacity(
    *,
    data: xr.DataArray,
    time_combiner: CoordCombinerProtocol,
    capacity: Optional[xr.DataArray] = None,
    min_capacity_factor: float = 0.0,
    max_capacity_factor: float = 1.0,
) -> xr.DataArray:
    x = accumulator_differences(x=data, time_combiner=time_combiner)
    return filter_by_capacity(
        data=x,
        capacity=capacity,
        min_capacity_factor=min_capacity_factor,
        max_capacity_factor=max_capacity_factor,
    )


def clamp(
    *, x: xr.DataArray, min_value: float | None = None, max_value: float | None = None
) -> xr.DataArray:
    """
    Clamp array values to specified minimum and maximum bounds.

    Args:
        x: Input data array to clamp
        min_value: Minimum value (optional)
        max_value: Maximum value (optional)

    Returns:
        Clamped data array with values constrained to bounds
    """
    if min_value is not None:
        x = np.maximum(x, min_value)  # type: ignore
    if max_value is not None:
        x = np.minimum(x, max_value)  # type: ignore
    return x


def verify_within_range(
    *,
    x: xr.DataArray,
    min_value: float | None = None,
    max_value: float | None = None,
    left_inclusive: bool = True,
    right_inclusive: bool = True,
) -> xr.DataArray:
    """
    Verify that all values in array are within specified range.

    Args:
        x: Input data array to verify
        min_value: Minimum allowed value (optional)
        max_value: Maximum allowed value (optional)
        left_inclusive: Whether minimum bound is inclusive (default: True)
        right_inclusive: Whether maximum bound is inclusive (default: True)

    Returns:
        Original array if all values are within range

    Raises:
        ValueError: If any values are outside the specified range
    """
    if x.isnull().all():
        return x
    if min_value is not None:
        if left_inclusive:
            condition = np.min(x) >= min_value
        else:
            condition = np.min(x) > min_value
        if not condition:
            raise ValidationError(
                f"{np.min(x)} is less than minimum value: {min_value}"
            )
    if max_value is not None:
        if right_inclusive:
            condition = np.max(x) <= max_value
        else:
            condition = np.max(x) < max_value
        if not condition:
            raise ValidationError(
                f"{np.max(x)} is greater than maximum value: {max_value}"
            )
    return x


def is_between_values(
    *,
    x: xr.DataArray,
    min_value: float | None = None,
    max_value: float | None = None,
    left_inclusive: bool = True,
    right_inclusive: bool = True,
) -> xr.DataArray:
    """
    Create boolean mask for values within specified range.

    Args:
        x: Input data array to check
        min_value: Minimum value for range (optional)
        max_value: Maximum value for range (optional)
        left_inclusive: Whether minimum bound is inclusive (default: True)
        right_inclusive: Whether maximum bound is inclusive (default: True)

    Returns:
        Boolean array indicating which values are within range
    """
    result = xr.ones_like(x, dtype=bool)
    if min_value is not None:
        if left_inclusive:
            result = result & (x >= min_value)
        else:
            result = result & (x > min_value)
    if max_value is not None:
        if right_inclusive:
            result = result & (x <= max_value)
        else:
            result = result & (x < max_value)
    return result


def filter_to_range(
    *,
    x: xr.DataArray,
    min_value: float | None = None,
    max_value: float | None = None,
    left_inclusive: bool = True,
    right_inclusive: bool = True,
) -> xr.DataArray:
    """
    Filter array to only include values within specified range.

    Args:
        x: Input data array to filter
        min_value: Minimum value for range (optional)
        max_value: Maximum value for range (optional)
        left_inclusive: Whether minimum bound is inclusive (default: True)
        right_inclusive: Whether maximum bound is inclusive (default: True)

    Returns:
        Filtered array with out-of-range values set to NaN
    """
    between = is_between_values(
        x=x,
        min_value=min_value,
        max_value=max_value,
        left_inclusive=left_inclusive,
        right_inclusive=right_inclusive,
    )
    return x.where(between)


def from_total_to_rate_of_change(
    *, x: xr.DataArray, time_unit_seconds: int = 3600
) -> xr.DataArray:
    """
    Convert total values to rate of change per time unit.

    Args:
        x: Input data array with total values
        time_unit_seconds: Target time unit in seconds (default: 3600 for hourly)

    Returns:
        Data array with rate of change values
    """
    return x * time_unit_seconds / calculate_seconds(x)


def from_rate_of_change_to_total(
    *, x: xr.DataArray, time_unit_seconds: int = 3600
) -> xr.DataArray:
    """
    Convert rate of change values to total values.

    Args:
        x: Input data array with rate of change values
        time_unit_seconds: Source time unit in seconds (default: 3600 for hourly)

    Returns:
        Data array with total values
    """
    return x * calculate_seconds(x) / time_unit_seconds


def diff(
    x: xr.DataArray,
    time_dim: Time = Time.TIME_5MIN_UTC,
) -> xr.DataArray:
    """
    Use this function instead of the .diff method in order to preserve the number of time steps.
    In most applications, we want the difference to be shown on the previous time step which
    matches the behavior of this function. The last time step will be NaN.
    For example, if you had a time series with steps ["2024-01-01 00:00:00", "2024-01-01 00:05:00", "2024-01-01 00:10:00"],
    and data points [1, 2, 3], this function would return [1, 1, NaN].
    """
    return x.shift({time_dim.value: -1}) - x


def all_not_null_mask(*arrays: xr.DataArray) -> xr.DataArray:
    return functools.reduce(operator.and_, [array.notnull() for array in arrays])


def availability(
    *, x: xr.DataArray, time_combiner: CoordCombinerProtocol
) -> xr.DataArray:
    """
    Calculate availability of a status array.

    Args:
        status: Status array
        time_combiner: Time combiner

    Returns:
        Availability array
    """
    return time_combiner.agg(1 - x, agg=Aggregation.MEAN)


def remove_flat_lining(
    *, x: xr.DataArray, time_combiner: CoordCombinerProtocol
) -> xr.DataArray:
    """
    Removes periods based on the time combiner where the max equals the min values.
    """
    agg_max = time_combiner.agg(x, agg=Aggregation.MAX)
    agg_min = time_combiner.agg(x, agg=Aggregation.MIN)
    is_flat = agg_max == agg_min
    is_flat_mask = time_combiner.broadcast(is_flat)
    return x.where(~is_flat_mask)
