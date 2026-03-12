import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from core.utils.pandas_datetime import index_to_numpy_ns, series_to_numpy_ns
from pydantic import ConfigDict, validate_call

from kpi_pipeline.base.enums import Time

arbitrary_types_allowed = ConfigDict(arbitrary_types_allowed=True)


@validate_call(config=arbitrary_types_allowed)
def pandas_device_time_series_to_xarray(
    dataframe: pd.DataFrame, device_type: DeviceType
) -> xr.DataArray:
    return xr.DataArray(
        data=dataframe.to_numpy(),
        dims=[Time.TIME_5MIN_UTC.value, device_type.name.lower()],
        coords={
            Time.TIME_5MIN_UTC.value: index_to_numpy_ns(index=dataframe.index),
            device_type.name.lower(): index_to_numpy_ns(index=dataframe.columns),
        },
    )


@validate_call(config=arbitrary_types_allowed)
def pandas_device_attributes_to_xarray(
    series: pd.Series, device_type: DeviceType
) -> xr.DataArray:
    return xr.DataArray(
        data=series_to_numpy_ns(series=series),
        dims=[device_type.name.lower()],
        coords={
            device_type.name.lower(): index_to_numpy_ns(index=series.index),
        },
    )


@validate_call(config=arbitrary_types_allowed)
def pandas_time_series_to_xarray(series: pd.Series) -> xr.DataArray:
    return xr.DataArray(
        data=series_to_numpy_ns(series=series),
        dims=[Time.TIME_5MIN_UTC.value],
        coords={
            Time.TIME_5MIN_UTC.value: index_to_numpy_ns(index=series.index),
        },
    )
