import xarray as xr

from kpi.base.enumeration import NEW_NAME, TimeCoord
from kpi.domain.util import diff, mod


def resample_first(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    """Take the first sample in each group defined by ``grouper``.

    Args:
        x: Values on a fine time (or index) grid.
        grouper: Coordinate or array used as the group key (e.g. local date).

    Returns:
        ``x.groupby(grouper).first()``.
    """
    return x.groupby(grouper).first()


def resample_diff(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    """First value per group, then :func:`~kpi.domain.util.diff` on group time.

    The group time coordinate is taken from ``grouper.attrs[NEW_NAME]``.

    Args:
        x: Series to bucket and difference.
        grouper: Grouping key whose attrs carry the resampled time coord name.

    Returns:
        Per-group first-differenced series on the grouped time axis.
    """
    return diff(
        resample_first(x, grouper=grouper), time_dim=TimeCoord(grouper.attrs[NEW_NAME])
    )


def resample_diff_mod(
    x: xr.DataArray, *, grouper: xr.DataArray, modulus: float
) -> xr.DataArray:
    """Modulo-wrapped grouped first difference (see :func:`resample_diff`).

    Args:
        x: Input series.
        grouper: Grouping key for resampling.
        modulus: Modulus for :func:`~kpi.domain.util.mod`.

    Returns:
        ``mod(resample_diff(x, grouper=grouper), modulus=modulus)``.
    """
    return mod(resample_diff(x, grouper=grouper), modulus=modulus)


def resample_sum(
    x: xr.DataArray, *, grouper: xr.DataArray, min_count: int = 1
) -> xr.DataArray:
    """Sum ``x`` within each ``grouper`` bucket.

    Args:
        x: Values to aggregate.
        grouper: Group labels aligned to ``x``.
        min_count: Minimum valid observations per group for a non-NaN sum.

    Returns:
        ``x.groupby(grouper).sum(min_count=min_count)``.
    """
    return x.groupby(grouper).sum(min_count=min_count)


def resample_min(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    """Minimum of ``x`` in each ``grouper`` group.

    Args:
        x: Values to aggregate.
        grouper: Group labels aligned to ``x``.

    Returns:
        ``x.groupby(grouper).min()``.
    """
    return x.groupby(grouper).min()


def resample_mean(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    """Mean of ``x`` in each ``grouper`` group.

    Args:
        x: Values to aggregate.
        grouper: Group labels aligned to ``x``.

    Returns:
        ``x.groupby(grouper).mean()``.
    """
    return x.groupby(grouper).mean()


def resample_max(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    """Maximum of ``x`` in each ``grouper`` group.

    Args:
        x: Values to aggregate.
        grouper: Group labels aligned to ``x``.

    Returns:
        ``x.groupby(grouper).max()``.
    """
    return x.groupby(grouper).max()
