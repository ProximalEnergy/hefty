import xarray as xr
from kpi.domain.agg.resample import resample_sum


def count_daily_hours_from_5m(
    *, bool_array_5m: xr.DataArray, date_local_5m: xr.DataArray
) -> xr.DataArray:
    return resample_sum(bool_array_5m, grouper=date_local_5m) * 5 / 60
