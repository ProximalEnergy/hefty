import xarray as xr

from kpi.domain.agg.resample import resample_sum
from kpi.domain.util import filter_mask


def count_daily_hours_from_5m(
    *, bool_array_5m: xr.DataArray, date_local_5m: xr.DataArray
) -> xr.DataArray:
    """Sum boolean 5-minute flags into hours per local calendar day.

    Each true 5-minute sample contributes 5/60 hour; results are grouped by
    ``date_local_5m``.

    Args:
        bool_array_5m: Boolean (or numeric) mask on the 5-minute time grid.
        date_local_5m: Local date coordinate aligned to each 5-minute step.

    Returns:
        Daily totals in hours (sum of 5-minute contributions).
    """
    return resample_sum(bool_array_5m, grouper=date_local_5m) * 5 / 60


def filter_energy_5m(
    *,
    energy_unfiltered_5m: xr.DataArray,
    power_capacity: xr.DataArray,
) -> xr.DataArray:
    """Reject 5-minute energy inconsistent with nameplate power capacity.

    Values are kept only when ``energy / power_capacity`` lies in
    ``[-eps, 1/12 + eps]``, i.e. at most one hour of energy at rated power per
    5-minute interval.

    Args:
        energy_unfiltered_5m: Interval energy on the 5-minute grid.
        power_capacity: Reference power capacity in consistent units.

    Returns:
        ``energy_unfiltered_5m`` with out-of-range points set to NaN.
    """
    epsilon = 1e-6
    return energy_unfiltered_5m.where(
        filter_mask(
            filter_by=energy_unfiltered_5m / power_capacity,
            min_value=-epsilon,
            max_value=1 / 12 + epsilon,
        )
    )


def filter_by_value(
    x: xr.DataArray,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
) -> xr.DataArray:
    return x.where(filter_mask(filter_by=x, min_value=min_value, max_value=max_value))
