import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.util import coord
from kpi.domain.util import rename


def daily_mean_across_devices(
    *,
    value: xr.DataArray,
    device_type: DeviceTypeEnum,
    date_local_5m: xr.DataArray,
) -> xr.DataArray:
    is_valid_sum = (
        value.notnull().sum(dim=coord(device_type)).groupby(rename(date_local_5m)).sum()
    )
    value_sum = value.sum(dim=coord(device_type)).groupby(rename(date_local_5m)).sum()
    return value_sum / is_valid_sum.where(is_valid_sum > 0)


def daily_mean_across_grouped_devices(
    *,
    value: xr.DataArray,
    device_mapping: xr.DataArray,
    device_type: DeviceTypeEnum,
    date_local_5m: xr.DataArray,
) -> xr.DataArray:
    is_valid_sum = (
        value.notnull()
        .groupby(device_mapping.rename(coord(device_type)))
        .sum()
        .groupby(rename(date_local_5m))
        .sum()
    )
    value_sum = (
        value.groupby(device_mapping.rename(coord(device_type)))
        .sum()
        .groupby(rename(date_local_5m))
        .sum()
    )
    return value_sum / is_valid_sum.where(is_valid_sum > 0)
