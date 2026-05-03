import xarray as xr
from kpi.domain.util import rename
from xarray.core.groupby import DataArrayGroupBy


def groupby(x: xr.DataArray, *, grouper: xr.DataArray) -> DataArrayGroupBy:
    return x.groupby(rename(grouper))


def resample_first(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    return groupby(x, grouper=grouper).first()


def resample_sum(
    x: xr.DataArray, *, grouper: xr.DataArray, min_count: int = 1
) -> xr.DataArray:
    return groupby(x, grouper=grouper).sum(min_count=min_count)


def resample_min(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    return groupby(x, grouper=grouper).min()


def resample_mean(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    return groupby(x, grouper=grouper).mean()


def resample_max(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    return groupby(x, grouper=grouper).max()
