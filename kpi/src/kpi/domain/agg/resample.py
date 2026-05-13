import xarray as xr
from kpi.base.enumeration import NEW_NAME, TimeCoord
from kpi.domain.util import diff, mod


def resample_first(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    return x.groupby(grouper).first()


def resample_diff(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    return diff(
        resample_first(x, grouper=grouper), time_dim=TimeCoord(grouper.attrs[NEW_NAME])
    )


def resample_diff_mod(
    x: xr.DataArray, *, grouper: xr.DataArray, modulus: float
) -> xr.DataArray:
    return mod(resample_diff(x, grouper=grouper), modulus=modulus)


def resample_sum(
    x: xr.DataArray, *, grouper: xr.DataArray, min_count: int = 1
) -> xr.DataArray:
    return x.groupby(grouper).sum(min_count=min_count)


def resample_min(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    return x.groupby(grouper).min()


def resample_mean(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    return x.groupby(grouper).mean()


def resample_max(x: xr.DataArray, *, grouper: xr.DataArray) -> xr.DataArray:
    return x.groupby(grouper).max()
