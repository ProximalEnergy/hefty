import warnings
from typing import overload

import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import TimeCoords
from kpi.base.exception import ValidationError
from kpi.base.util import coord
from kpi.base.warning import ValidationWarning


def prefix(x: xr.DataArray) -> str:
    return f"{x.name}: " if x.name else ""


def verify_positive(x: xr.DataArray) -> xr.DataArray:
    epsilon = 1e-6
    x_min = x.min()
    if x_min.isnull():
        raise ValidationError(f"{prefix(x)}value is NaN")
    if x_min < epsilon:
        raise ValidationError(f"{prefix(x)}value is non-positive: {x.min().item()}")
    return x


def diff(
    x: xr.DataArray,
    time_dim: TimeCoords = TimeCoords.TIME_5MIN_UTC,
) -> xr.DataArray:
    """
    Like ``.diff`` but keeps the same length: change is attributed to the prior
    step; the last value is NaN.

    Example: times
    ``["2024-01-01 00:00:00", "2024-01-01 00:05:00", "2024-01-01 00:10:00"]``
    with values ``[1, 2, 3]`` yields ``[1, 1, NaN]``.
    """
    return x.shift({time_dim.value: -1}) - x


def cumsum(
    x: xr.DataArray,
    time_dim: TimeCoords = TimeCoords.TIME_5MIN_UTC,
    skipna: bool = True,
) -> xr.DataArray:
    """
    Inverse of diff(): at each time stamp, the value is the sum of all
    differences before that stamp (first stamp is 0). Preserves the time axis.
    For diff output [1, 1, NaN], returns [0, 1, 2].
    """
    dim = time_dim.value
    shifted = x.cumsum(dim=dim, skipna=skipna).shift({dim: 1})
    shifted.loc[{dim: shifted.coords[dim][0]}] = 0
    return shifted


def filter_mask(
    *,
    filter_by: xr.DataArray,
    min_value: float | None = None,
    max_value: float | None = None,
) -> xr.DataArray:
    if min_value is not None and filter_by.min() < min_value:
        warnings.warn(
            (
                f"{prefix(filter_by)}value is less than {min_value}: "
                f"{filter_by.min().item()}"
            ),
            ValidationWarning,
        )
    if max_value is not None and filter_by.max() > max_value:
        warnings.warn(
            (
                f"{prefix(filter_by)}value is greater than {max_value}: "
                f"{filter_by.max().item()}"
            ),
            ValidationWarning,
        )
    mask = xr.DataArray(True, dims=filter_by.dims, coords=filter_by.coords)
    if min_value is not None:
        mask &= filter_by >= min_value
    if max_value is not None:
        mask &= filter_by <= max_value
    return mask


def filter_verify(
    *,
    filter_by: xr.DataArray,
    min_value: float | None = None,
    max_value: float | None = None,
) -> xr.DataArray:
    if min_value is not None and filter_by.min() < min_value:
        raise ValidationError(
            (
                f"{prefix(filter_by)}value is less than {min_value}: "
                f"{filter_by.min().item()}"
            ),
        )
    if max_value is not None and filter_by.max() > max_value:
        raise ValidationError(
            (
                f"{prefix(filter_by)}value is greater than {max_value}: "
                f"{filter_by.max().item()}"
            ),
        )
    return filter_by


def filter_tracker(
    degree: xr.DataArray,
    *,
    min_angle: float = -90,
    max_angle: float = 90,
) -> xr.DataArray:
    return degree.where(
        filter_mask(filter_by=degree, min_value=min_angle, max_value=max_angle)
    )


def filter_capacity(
    *,
    value: xr.DataArray,
    capacity: xr.DataArray,
    min_capacity_factor: float = 0.0,
    max_capacity_factor: float = 1.0,
) -> xr.DataArray:
    epsilon = 1e-6
    return value.where(
        filter_mask(
            filter_by=value / capacity,
            min_value=min_capacity_factor - epsilon,
            max_value=max_capacity_factor + epsilon,
        )
    )


def daily_mean_across_devices(
    *,
    value: xr.DataArray,
    device_type: DeviceType,
    date_local_5m: xr.DataArray,
) -> xr.DataArray:
    is_valid_sum = (
        value.notnull()
        .sum(dim=coord(device_type))
        .groupby(date_local(date_local_5m))
        .sum()
    )
    value_sum = (
        value.sum(dim=coord(device_type)).groupby(date_local(date_local_5m)).sum()
    )
    return value_sum / is_valid_sum.where(is_valid_sum > 0)


def daily_mean_across_grouped_devices(
    *,
    value: xr.DataArray,
    device_mapping: xr.DataArray,
    device_type: DeviceType,
    date_local_5m: xr.DataArray,
) -> xr.DataArray:
    is_valid_sum = (
        value.notnull()
        .groupby(device_mapping.rename(coord(device_type)))
        .sum()
        .groupby(date_local(date_local_5m))
        .sum()
    )
    value_sum = (
        value.groupby(device_mapping.rename(coord(device_type)))
        .sum()
        .groupby(date_local(date_local_5m))
        .sum()
    )
    return value_sum / is_valid_sum.where(is_valid_sum > 0)


@overload
def scale_offset(
    value: None,
    *,
    scale: float | None = None,
    offset: float | None = None,
) -> None: ...


@overload
def scale_offset(
    value: xr.DataArray,
    *,
    scale: float | None = None,
    offset: float | None = None,
) -> xr.DataArray: ...


def scale_offset(
    value: xr.DataArray | None,
    *,
    scale: float | None = None,
    offset: float | None = None,
) -> xr.DataArray | None:
    if value is None:
        return None
    if scale is not None:
        value *= scale
    if offset is not None:
        value += offset
    return value


def fill_accumulator(
    value: xr.DataArray,
) -> xr.DataArray:
    return value.ffill(dim=TimeCoords.TIME_5MIN_UTC.value).bfill(
        dim=TimeCoords.TIME_5MIN_UTC.value
    )


def date_local(
    date_local_5m: xr.DataArray,
) -> xr.DataArray:
    return date_local_5m.rename(TimeCoords.DATE_LOCAL.value)
