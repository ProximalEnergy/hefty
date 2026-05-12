import xarray as xr
from kpi.domain.agg.resample import resample_sum
from kpi.domain.util import filter_mask


def count_daily_hours_from_5m(
    *, bool_array_5m: xr.DataArray, date_local_5m: xr.DataArray
) -> xr.DataArray:
    return resample_sum(bool_array_5m, grouper=date_local_5m) * 5 / 60


def filter_energy_5m(
    *,
    energy_unfiltered_5m: xr.DataArray,
    power_capacity: xr.DataArray,
) -> xr.DataArray:
    """
    Reject 5-minute energy values that exceed 1/12 of the power capacity.
    """
    epsilon = 1e-6
    return energy_unfiltered_5m.where(
        filter_mask(
            filter_by=energy_unfiltered_5m / power_capacity,
            min_value=-epsilon,
            max_value=1 / 12 + epsilon,
        )
    )
