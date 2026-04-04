import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import TimeCoords
from kpi.base.exception import NoDownloadedDataError
from kpi.base.util import coord
from kpi.infra.util import index_to_numpy_ns, series_to_numpy_ns
from pydantic import ConfigDict, validate_call

arbitrary_types_allowed = ConfigDict(arbitrary_types_allowed=True)


@validate_call(config=arbitrary_types_allowed)
def pandas_time_series_to_xarray(series: pd.Series) -> xr.DataArray:
    return xr.DataArray(
        data=series_to_numpy_ns(series=series),
        dims=[TimeCoords.TIME_5MIN_UTC.value],
        coords={
            TimeCoords.TIME_5MIN_UTC.value: index_to_numpy_ns(index=series.index),
        },
    )


@validate_call(config=arbitrary_types_allowed)
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
    skip_if_project_level_empty: bool = False,
) -> xr.DataArray | None:
    if project_level:
        if df.empty:
            if skip_if_project_level_empty:
                return None
            raise NoDownloadedDataError(
                "Filtered dataframe for project level time series is empty"
            )
        if len(df.columns) > 1:
            raise ValueError(
                "Expected 1 column for project level time series, "
                f"got {len(df.columns)}"
            )
        return pandas_time_series_to_xarray(series=df.iloc[:, 0])
    return pandas_device_time_series_to_xarray(dataframe=df, device_type=device_type)
