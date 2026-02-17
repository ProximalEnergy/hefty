import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from pydantic import ConfigDict, validate_call

from kpi_pipeline.base.enums import Time

arbitrary_types_allowed = ConfigDict(arbitrary_types_allowed=True)


@validate_call(config=arbitrary_types_allowed)
def pandas_device_time_series_to_xarray(
    dataframe: pd.DataFrame, device_type: DeviceType
) -> xr.DataArray:
    return xr.DataArray(
        data=dataframe.values,
        dims=[Time.TIME_5MIN_UTC.value, device_type.name.lower()],
        coords={
            Time.TIME_5MIN_UTC.value: dataframe.index.values,
            device_type.name.lower(): dataframe.columns.values,
        },
    )


@validate_call(config=arbitrary_types_allowed)
def pandas_device_attributes_to_xarray(
    series: pd.Series, device_type: DeviceType
) -> xr.DataArray:
    return xr.DataArray(
        data=series.values,
        dims=[device_type.name.lower()],
        coords={
            device_type.name.lower(): series.index.values,
        },
    )


@validate_call(config=arbitrary_types_allowed)
def pandas_time_series_to_xarray(series: pd.Series) -> xr.DataArray:
    return xr.DataArray(
        data=series.values,
        dims=[Time.TIME_5MIN_UTC.value],
        coords={Time.TIME_5MIN_UTC.value: series.index.values},
    )
