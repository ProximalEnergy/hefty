import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.util import coord


def mean_across_devices(
    x: xr.DataArray,
    *,
    device_type: DeviceTypeEnum,
) -> xr.DataArray:
    return x.mean(dim=coord(device_type))


def sum_across_devices(
    x: xr.DataArray,
    *,
    device_type: DeviceTypeEnum,
    min_count: int = 1,
) -> xr.DataArray:
    return x.sum(dim=coord(device_type), min_count=min_count)


def min_across_devices(
    x: xr.DataArray,
    *,
    device_type: DeviceTypeEnum,
) -> xr.DataArray:
    return x.min(dim=coord(device_type))


def max_across_devices(
    x: xr.DataArray,
    *,
    device_type: DeviceTypeEnum,
) -> xr.DataArray:
    return x.max(dim=coord(device_type))
