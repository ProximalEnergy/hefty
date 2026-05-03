import warnings
from typing import SupportsFloat

import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.enumeration import NEW_NAME, TimeCoords
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


def apply_filter(
    x: xr.DataArray,
    min_value: float | None = None,
    max_value: float | None = None,
) -> xr.DataArray:
    return x.where(filter_mask(filter_by=x, min_value=min_value, max_value=max_value))


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
    return apply_filter(degree, min_value=min_angle, max_value=max_angle)


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


def scale_offset(
    value: xr.DataArray,
    *,
    scale: float | None = None,
    offset: float | None = None,
) -> xr.DataArray:
    if scale is not None:
        value = value * scale
    if offset is not None:
        value = value + offset
    return value


def fill_accumulator(
    value: xr.DataArray,
) -> xr.DataArray:
    return value.ffill(dim=TimeCoords.TIME_5MIN_UTC.value).bfill(
        dim=TimeCoords.TIME_5MIN_UTC.value
    )


def rename(
    x: xr.DataArray,
):
    return x.rename(x.attrs[NEW_NAME])


def fill_missing_zero(
    x: xr.DataArray,
) -> xr.DataArray:
    """
    Fill missing values with 0.
    """
    return x.fillna(0)


def fill_na_with_arrays(*args: xr.DataArray | None) -> xr.DataArray:
    x = xr.DataArray()
    for arg in args:
        if arg is not None:
            x, arg = xr.align(x, arg, join="outer")
            x = x.fillna(arg)
    return x


def sum_arrays(*args: xr.DataArray) -> xr.DataArray:
    concat = xr.concat(args, dim="temp")
    return concat.sum(dim="temp", min_count=1)


def infer_device_dim(x: xr.DataArray) -> str:
    device_coords = {coord(device_type) for device_type in DeviceTypeEnum}
    device_dims = [
        dim for dim in x.dims if isinstance(dim, str) and dim in device_coords
    ]
    if len(device_dims) > 1:
        raise ValueError(f"Multiple device dimensions found: {device_dims}")
    if len(device_dims) == 0:
        raise ValueError("No device dimension found")
    return device_dims[0]


def infer_time_dim(x: xr.DataArray) -> str:
    time_coords = {time_coord.value for time_coord in TimeCoords}
    time_dims = [dim for dim in x.dims if isinstance(dim, str) and dim in time_coords]
    if len(time_dims) > 1:
        raise ValueError(f"Multiple time dimensions found: {time_dims}")
    if len(time_dims) == 0:
        raise ValueError("No time dimension found")
    return time_dims[0]


def is_empty(x: xr.DataArray) -> bool:
    return (x.size == 0) or bool(x.isnull().all().item())


def get_single_float_value(x: xr.DataArray | SupportsFloat) -> float:
    if isinstance(x, xr.DataArray):
        return float(x.item())
    return float(x)


def available_from_event(
    event_change: xr.DataArray,
) -> xr.DataArray:
    """
    Calculates whether the 5-minute interval is available from event step changes.
    The `event_change` parameter is the number of events that began
    minus the number of events that ended in the 5-minute interval.
    It's assumed that every event has a start and end within the entire
    period. Events that began before the start date should have been counted
    as starting on the first time step, and events that finished after
    the end date should have been counted as ending on the last time step.
    This calculation does a forward cumulative sum to effectively determine
    the number of events that are active for each point in time.
    Intervals where the cumulative sum is greater than 0 are in an event and
    result in False, and intervals where the cumulative sum is 0 are not in an event
    and result in True.
    """
    return event_change.cumsum(dim=TimeCoords.TIME_5MIN_UTC.value) <= 0


def where(
    x: xr.DataArray,
    condition: xr.DataArray,
) -> xr.DataArray:
    return x.where(condition)
