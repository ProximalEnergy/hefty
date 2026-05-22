import warnings
from typing import SupportsFloat

import pandas as pd
import xarray as xr

from kpi.base.enumeration import NEW_NAME, TIME_DESCRIPTOR, TimeCoord
from kpi.base.exception import ValidationError
from kpi.base.warning import ValidationWarning


def prefix(x: xr.DataArray) -> str:
    """Build a short prefix from ``x``'s name for validation messages.

    Args:
        x: DataArray whose optional ``name`` is used in error text.

    Returns:
        ``"{name}: "`` when ``x.name`` is set; otherwise ``""``.
    """
    return f"{x.name}: " if x.name else ""


def verify_positive(x: xr.DataArray) -> xr.DataArray:
    """Require that all values in ``x`` are strictly positive and not NaN.

    Args:
        x: DataArray to validate.

    Returns:
        ``x`` when every finite element exceeds a small epsilon.

    Raises:
        ValidationError: If the minimum is NaN or below ``1e-6``.
    """
    epsilon = 1e-6
    x_min = x.min()
    if x_min.isnull():
        raise ValidationError(f"{prefix(x)}value is NaN")
    if x_min < epsilon:
        raise ValidationError(f"{prefix(x)}value is non-positive: {x.min().item()}")
    return x


def diff(
    x: xr.DataArray,
    time_dim: TimeCoord = TimeCoord.TIME_5MIN_UTC,
) -> xr.DataArray:
    """Backward step change on the time axis with unchanged length.

    Like ``xarray.DataArray.diff`` but attributes each increment to the prior
    timestep so the series length is preserved; the final timestep is NaN.

    Example: times
    ``["2024-01-01 00:00:00", "2024-01-01 00:05:00", "2024-01-01 00:10:00"]``
    with values ``[1, 2, 3]`` yields ``[1, 1, NaN]``.

    Args:
        x: Series differentiated along ``time_dim``.
        time_dim: Time coordinate enum for the differentiation dimension.

    Returns:
        ``x.shift({time_dim: -1}) - x``.
    """
    return x.shift({time_dim.value: -1}) - x


def cumsum(
    x: xr.DataArray,
    time_dim: TimeCoord = TimeCoord.TIME_5MIN_UTC,
    skipna: bool = True,
) -> xr.DataArray:
    """Cumulative sum of backward differences (inverse of :func:`diff`).

    At each timestamp the value is the sum of all prior per-step increments;
    the first timestamp is forced to zero. For ``diff`` output ``[1, 1, NaN]``,
    this returns ``[0, 1, 2]``.

    Args:
        x: Per-step increments (typically output of :func:`diff`).
        time_dim: Time dimension over which to accumulate.
        skipna: Forwarded to ``xarray.DataArray.cumsum``.

    Returns:
        Cumulative totals aligned with ``x``'s time coordinate.
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
    """Boolean mask true where ``filter_by`` lies within optional bounds.

    Emits :class:`ValidationWarning` when extrema fall outside ``min_value`` or
    ``max_value`` (soft check); the returned mask still encodes the hard bounds.

    Args:
        filter_by: Values compared against ``min_value`` and ``max_value``.
        min_value: Inclusive lower bound, or ``None`` to omit.
        max_value: Inclusive upper bound, or ``None`` to omit.

    Returns:
        DataArray of booleans aligned to ``filter_by``.
    """
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
    """Mask ``x`` to NaN where it falls outside optional numeric bounds.

    Args:
        x: Values to filter in place via ``where``.
        min_value: Inclusive lower bound for ``x``, or ``None``.
        max_value: Inclusive upper bound for ``x``, or ``None``.

    Returns:
        ``x.where(...)`` using :func:`filter_mask` on ``x``.
    """
    return x.where(filter_mask(filter_by=x, min_value=min_value, max_value=max_value))


def filter_verify(
    *,
    filter_by: xr.DataArray,
    min_value: float | None = None,
    max_value: float | None = None,
) -> xr.DataArray:
    """Hard-validate that ``filter_by`` extrema lie within bounds.

    Args:
        filter_by: Series whose min and max are checked.
        min_value: If set, require ``filter_by.min() >= min_value``.
        max_value: If set, require ``filter_by.max() <= max_value``.

    Returns:
        ``filter_by`` unchanged when checks pass.

    Raises:
        ValidationError: When a bound is violated.
    """
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
    """Mask tracker angles outside a symmetric tilt range.

    Args:
        degree: Tracker angle in degrees.
        min_angle: Inclusive lower bound (default -90).
        max_angle: Inclusive upper bound (default 90).

    Returns:
        ``degree`` with out-of-range values set to NaN.
    """
    return apply_filter(degree, min_value=min_angle, max_value=max_angle)


def filter_capacity(
    *,
    value: xr.DataArray,
    capacity: xr.DataArray,
    min_capacity_factor: float = 0.0,
    max_capacity_factor: float = 1.0,
) -> xr.DataArray:
    """Mask ``value`` where its ratio to ``capacity`` is out of range.

    Keeps points where ``value / capacity`` is within
    ``[min_capacity_factor - eps, max_capacity_factor + eps]``.

    Args:
        value: Magnitude to compare (e.g. power or energy rate).
        capacity: Positive capacity in consistent units.
        min_capacity_factor: Lower ratio bound (inclusive before epsilon slack).
        max_capacity_factor: Upper ratio bound (inclusive before epsilon slack).

    Returns:
        ``value`` with invalid ratios masked to NaN.
    """
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
    """Apply optional linear scaling and offset to ``value``.

    Args:
        value: Input array.
        scale: If set, multiply ``value`` by this factor.
        offset: If set, add this constant after scaling.

    Returns:
        Transformed ``value`` (identity when both arguments are ``None``).
    """
    if scale is not None:
        value = value * scale
    if offset is not None:
        value = value + offset
    return value


def fill_accumulator(
    value: xr.DataArray,
) -> xr.DataArray:
    """Forward- then backward-fill along the 5-minute UTC time axis.

    Args:
        value: Series with possible gaps on ``TIME_5MIN_UTC``.

    Returns:
        ``value`` with gaps filled from neighbors on that dimension.
    """
    return value.ffill(dim=TimeCoord.TIME_5MIN_UTC.value).bfill(
        dim=TimeCoord.TIME_5MIN_UTC.value
    )


def fill_missing_zero(
    x: xr.DataArray,
) -> xr.DataArray:
    """Replace NaN elements with zero.

    Args:
        x: Input array.

    Returns:
        ``x.fillna(0)``.
    """
    return x.fillna(0)


def fill_na_with_arrays(*args: xr.DataArray | None) -> xr.DataArray:
    """Outer-align arrays and coalesce NaNs using the first non-null at each point.

    Args:
        *args: Any number of optional DataArrays; ``None`` entries are skipped.

    Returns:
        Single array with NaNs filled from later arguments in argument order.
    """
    x = xr.DataArray()
    for arg in args:
        if arg is not None:
            x, arg = xr.align(x, arg, join="outer")
            x = x.fillna(arg)
    return x


def sum_arrays(*args: xr.DataArray | None) -> xr.DataArray:
    """Elementwise sum of non-``None`` arrays along a temporary concat dimension.

    Args:
        *args: DataArrays to sum; ``None`` values are ignored.

    Returns:
        Sum over a synthetic ``temp`` dimension with ``min_count=1``.
    """
    concat = xr.concat([arg for arg in args if arg is not None], dim="temp")
    return concat.sum(dim="temp", min_count=1)


def is_empty(x: xr.DataArray) -> bool:
    """Return whether ``x`` has no elements or is entirely NaN.

    Args:
        x: DataArray to inspect.

    Returns:
        ``True`` if size is zero or all values are null.
    """
    return (x.size == 0) or bool(x.isnull().all().item())


def get_single_float_value(x: xr.DataArray | SupportsFloat) -> float:
    """Coerce a scalar DataArray or float-like object to ``float``.

    Args:
        x: Single-element DataArray or a type supporting ``float()``.

    Returns:
        Python ``float`` for the sole value.

    Raises:
        ValueError: Propagated from ``DataArray.item()`` if not scalar.
    """
    if isinstance(x, xr.DataArray):
        return float(x.item())
    return float(x)


def available_from_event(
    event_change: xr.DataArray,
) -> xr.DataArray:
    """Mark 5-minute steps as available (not inside an outage/event window).

    ``event_change`` is the count of events that started minus events that ended
    in each interval. A forward cumulative sum yields the number of concurrent
    active events; steps with a positive running total are treated as in-event
    (unavailable). Edge events should be aligned so starts before the series and
    ends after the series are reflected at the first/last timestep.

    Args:
        event_change: Net event starts minus ends per 5-minute step.

    Returns:
        Boolean-like array, true where cumulative event count is zero.
    """
    return event_change.cumsum(dim=TimeCoord.TIME_5MIN_UTC.value) <= 0


def where(
    x: xr.DataArray,
    condition: xr.DataArray,
) -> xr.DataArray:
    """Apply ``x.where(condition)`` as a thin wrapper for readability.

    Args:
        x: Values to mask.
        condition: Boolean mask aligned to ``x``.

    Returns:
        ``x.where(condition)``.
    """
    return x.where(condition)


def time_grouper(
    from_time: pd.DatetimeIndex,
    from_time_coord: TimeCoord,
    to_time_coord: TimeCoord,
    time_zone: str | None = None,
) -> xr.DataArray:
    """Build a grouping coordinate that floors timestamps to a target frequency.

    Converts ``from_time`` according to ``from_time_coord`` metadata, floors to
    the pandas frequency of ``to_time_coord``, and returns a DataArray whose
    coords map original times to grouped bucket labels.

    Args:
        from_time: DatetimeIndex (typically tz-aware) for the source grid.
        from_time_coord: Source :class:`TimeCoord` describing ``from_time``.
        to_time_coord: Target bucket frequency and naming via ``TIME_DESCRIPTOR``.
        time_zone: Required when ``to_time_coord`` is not UTC; used for
            ``tz_convert`` before flooring.

    Returns:
        DataArray of floored timestamps with ``NEW_NAME`` attr set to the target
        time coord string.

    Raises:
        ValueError: If a non-UTC target is requested without ``time_zone``.
    """
    to_time_descriptor = TIME_DESCRIPTOR[to_time_coord]

    if to_time_descriptor.utc:
        new_time = from_time.tz_convert("UTC")
    else:
        if time_zone is None:
            raise ValueError(
                "Time zone is required when converting to a non-UTC time coordinate"
            )
        new_time = from_time.tz_convert(time_zone)

    grouped_time = (
        new_time.tz_localize(None).floor(to_time_descriptor.pandas_freq).to_numpy()
    )

    return xr.DataArray(
        grouped_time,
        dims=[from_time_coord.value],
        coords={from_time_coord.value: from_time.tz_localize(None).values},
        attrs={
            NEW_NAME: to_time_coord.value,
        },
    )


def mod(x: xr.DataArray, modulus: float) -> xr.DataArray:
    """Floating modulo with a small epsilon shift to stabilize boundaries.

    Args:
        x: Dividend values.
        modulus: Strictly positive modulus.

    Returns:
        ``((x + epsilon) % modulus) - epsilon`` with ``epsilon = 1e-6``.
    """
    epsilon = 1e-6
    return ((x + epsilon) % modulus) - epsilon


def diff_mod(
    x: xr.DataArray, *, modulus: float, time_dim: TimeCoord = TimeCoord.TIME_5MIN_UTC
) -> xr.DataArray:
    """Modulo-wrapped backward difference on a time dimension.

    Args:
        x: Series differentiated then reduced modulo ``modulus`` (e.g. angles).
        modulus: Modulus passed to :func:`mod`.
        time_dim: Time coordinate for :func:`diff`.

    Returns:
        ``mod(diff(x, time_dim=time_dim), modulus=modulus)``.
    """
    return mod(diff(x, time_dim=time_dim), modulus=modulus)
