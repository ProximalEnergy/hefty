import xarray as xr
from kpi.domain.util import filter_mask


def pv_filter_daily_energy(
    *,
    energy_unfiltered_d: xr.DataArray,
    power_capacity: xr.DataArray,
    max_specific_yield: float = 24,
) -> xr.DataArray:
    """
    Reject daily energy totals that are negative or exceed the maximum specific yield.
    """
    epsilon = 1e-6
    return energy_unfiltered_d.where(
        filter_mask(
            filter_by=energy_unfiltered_d / power_capacity,
            min_value=-epsilon,
            max_value=max_specific_yield,
        )
    )
