import pandas as pd
import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.enumeration import TimeCoord


def get_time_dimension(x: xr.DataArray) -> TimeCoord:
    time_dims = [str(dim) for dim in x.dims if dim in TimeCoord]
    if len(time_dims) > 1:
        raise ValueError(f"Multiple time dimensions found: {time_dims}")
    if len(time_dims) == 0:
        raise ValueError("No time dimension found")
    return TimeCoord(time_dims[0])


def get_device_dimension(x: xr.DataArray) -> DeviceTypeEnum:
    device_types = [device.name.lower() for device in DeviceTypeEnum]
    device_dims = [str(dim) for dim in x.dims if dim in device_types]
    if len(device_dims) > 1:
        raise ValueError(f"Multiple device dimensions found: {device_dims}")
    if len(device_dims) == 0:
        raise ValueError("No device dimension found")
    return DeviceTypeEnum[device_dims[0].upper()]


def xarray_device_time_series_to_pandas(x: xr.DataArray) -> pd.DataFrame:
    time_dim = get_time_dimension(x)
    device_dim = get_device_dimension(x)
    return x.transpose(time_dim.value, device_dim.name.lower()).to_pandas()  # type: ignore


def xarray_time_series_to_pandas(x: xr.DataArray) -> pd.Series:
    if len(x.dims) > 1:
        raise ValueError(
            f"Too many dimensions for time series: {x.dims} in xr.DataArray {x.name}"
        )
    time_dim = get_time_dimension(x)
    return x.transpose(time_dim.value).to_pandas()  # type: ignore
