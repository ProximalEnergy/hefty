import numpy as np
import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from core.utils.pandas_datetime import index_to_numpy_ns
from kpi.base.enumeration import TimeCoords
from kpi.base.util import coord


def pandas_time_series_to_xarray(series: pd.Series) -> xr.DataArray:
    return xr.DataArray(
        data=series.to_numpy(),
        dims=[TimeCoords.TIME_5MIN_UTC.value],
        coords={
            TimeCoords.TIME_5MIN_UTC.value: index_to_numpy_ns(index=series.index),
        },
    )


def pandas_project_df_to_xarray(df: pd.DataFrame) -> xr.DataArray:
    if len(df.columns) > 1:
        raise ValueError(
            f"Expected 1 column for project level time series, got {len(df.columns)}"
        )
    if len(df.columns) == 0:
        array = np.array([])
    else:
        array = df.iloc[:, 0].to_numpy()
    return xr.DataArray(
        data=array,
        dims=[TimeCoords.TIME_5MIN_UTC.value],
        coords={
            TimeCoords.TIME_5MIN_UTC.value: index_to_numpy_ns(index=df.index),
        },
    )


def pandas_device_time_series_to_xarray(
    dataframe: pd.DataFrame, device_type: DeviceType
) -> xr.DataArray:
    return xr.DataArray(
        data=dataframe.to_numpy(),
        dims=[TimeCoords.TIME_5MIN_UTC.value, coord(device_type)],
        coords={
            TimeCoords.TIME_5MIN_UTC.value: index_to_numpy_ns(index=dataframe.index),
            coord(device_type): index_to_numpy_ns(index=dataframe.columns),
        },
    )


def dataframe_to_xarray(
    df: pd.DataFrame,
    *,
    project_level: bool,
    device_type: DeviceType,
) -> xr.DataArray:
    if project_level:
        return pandas_project_df_to_xarray(df=df)
    return pandas_device_time_series_to_xarray(dataframe=df, device_type=device_type)
