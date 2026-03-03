import datetime
from contextlib import contextmanager
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr
from kpi_pipeline.base.enums import (
    UTC,
    Aggregation,
    DataType,
    Time,
    freq_map,
    is_utc_map,
)
from kpi_pipeline.base.protocols import ObserverProtocol
from kpi_pipeline.infra.exceptions import (
    DatasetAccessError,
    DataTypeCastingError,
    EmptyDataArrayError,
)
from numpy.typing import NDArray
from pydantic import ConfigDict

arbitrary_types_allowed = ConfigDict(arbitrary_types_allowed=True)

NANOSECONDS = "ns"


@np.vectorize
def vectorized_hex_to_int(hex_val):
    """Safely converts a hex string to an integer, returning np.nan on failure."""
    try:
        return int(hex_val, 16)
    except (ValueError, TypeError):
        return np.nan


class Result:
    def __init__(self):
        self.value: xr.DataArray | None = None


@contextmanager
def assign_var(
    *,
    observer: ObserverProtocol,
    var: str,
    dataset: xr.Dataset,
    dtype: DataType | None = None,
    scale: float | None = None,
    offset: float | None = None,
    fill_value: Any | None = None,
):
    with observer.watch(var=var):
        result = Result()
        yield result
        if result.value is None:
            raise ValueError(f"data array for {var} is None")
        result.value = xr.DataArray(result.value)
        if result.value.size == 0:
            raise EmptyDataArrayError(f"data array for {var} is empty")
        if dtype is not None:
            try:
                result.value = result.value.astype(dtype)
            except ValueError as e:
                raise DataTypeCastingError(str(e)) from e
        if result.value.isnull().all():
            raise EmptyDataArrayError(f"data array for {var} values are all null")
        if scale is not None:
            result.value = result.value * scale
        if offset is not None:
            result.value = result.value + offset
        dataset[var] = result.value.reindex_like(dataset, fill_value=fill_value)


def xarray_agg(
    x: xr.DataArray | xr.core.groupby.DataArrayGroupBy,
    agg: Aggregation,
    dim=...,
    **kwargs: Any,
) -> xr.DataArray:
    return getattr(x, agg.value)(dim=dim, **kwargs)  # type: ignore


def fillna(*arrays: xr.DataArray) -> xr.DataArray:
    x = xr.DataArray()
    for array in arrays:
        x = x.fillna(array)
    return x


def invert_injective_dict[T, K](original_dict: dict[T, K]) -> dict[K, T]:
    """
    Inverts a dictionary by first checking if it's invertible.

    Raises:
        ValueError: If the original dictionary contains duplicate values.
    """
    values = original_dict.values()

    # A set only contains unique elements.
    # If the number of values is not equal to the number of unique values,
    # then duplicates must exist.
    if len(values) != len(set(values)):
        raise ValueError(
            "Duplicate values found. Cannot invert non-injective dictionary."
        )

    # If the check passes, we can safely invert using a comprehension
    return {value: key for key, value in original_dict.items()}


class VectorizedMap[T, K]:
    def __init__(self, map: dict[T, K]):
        self.map = map

    @np.vectorize
    def __call__(self, x: T) -> K:
        return self.map[x]


def select(dataset: xr.Dataset, var: str) -> xr.DataArray:
    try:
        return dataset[var]
    except KeyError as e:
        raise DatasetAccessError(str(e)) from e


def optional(dataset: xr.Dataset, var: str | None) -> xr.DataArray | None:
    if var is not None and var in dataset:
        return dataset[var]
    return None


def filter_by_time_range_utc[T: xr.DataArray | xr.Dataset](
    x: T,
    start_time_utc: np.datetime64 | None = None,
    end_time_utc: np.datetime64 | None = None,
    left_inclusive: bool = True,
    right_inclusive: bool = False,
) -> T:
    condition = xr.DataArray(True)
    if start_time_utc is not None:
        if left_inclusive:
            condition = condition & (
                x.coords[Time.TIME_5MIN_UTC.value] >= start_time_utc
            )
        else:
            condition = condition & (
                x.coords[Time.TIME_5MIN_UTC.value] > start_time_utc
            )
    if end_time_utc is not None:
        if right_inclusive:
            condition = condition & (x.coords[Time.TIME_5MIN_UTC.value] <= end_time_utc)
        else:
            condition = condition & (x.coords[Time.TIME_5MIN_UTC.value] < end_time_utc)
    return x.where(condition, drop=True)  # type: ignore


def to_local(x: NDArray[np.datetime64], time_zone: str) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(x).tz_localize(UTC).tz_convert(time_zone)


def to_utc(x: pd.DatetimeIndex) -> NDArray[np.datetime64]:
    return x.tz_convert(UTC).tz_localize(None).to_numpy()


def pandas_timestamp_to_datetime64_utc(x: pd.Timestamp) -> np.datetime64:
    return np.datetime64(  # type: ignore
        x.tz_convert(UTC).tz_localize(None), NANOSECONDS
    )


def broadcast(*, x: xr.DataArray, mapped_coordinates: xr.DataArray) -> xr.DataArray:
    """
    Broadcast data array using mapped coordinates.

    This function selects values from the input array using mapped coordinates
    and resets coordinates to create a broadcasted result.

    Args:
        x: Input data array to broadcast
        mapped_coordinates: Coordinate mapping array (must have a name)

    Returns:
        Broadcasted data array with coordinates reset

    Raises:
        ValueError: If mapped_coordinates has no name
    """
    # The name of the mapped_coordinates array should be the of the axis of the input
    # and the coordinates in should match the axis of the output
    if mapped_coordinates.name is None:
        raise ValueError("mapped_coordinates must have a name")
    return x.sel({str(mapped_coordinates.name): mapped_coordinates}).reset_coords(
        drop=True
    )


def resampled_array(
    *,
    high_frequency_time_axis: Time,
    low_frequency_time_axis: Time,
    time_zone: str,
    time: NDArray[np.datetime64],
) -> pd.DatetimeIndex:
    # convert time to pandas time index
    pandas_time = pd.DatetimeIndex(time)

    # localize the pandas time based on the form of the time axis
    if is_utc_map[high_frequency_time_axis]:
        pandas_time_localized = pandas_time.tz_localize(UTC)
    else:
        pandas_time_localized = pandas_time.tz_localize(time_zone)

    # determine whether new time axis is utc or local
    if is_utc_map[low_frequency_time_axis]:
        converted_time_zone = UTC
    else:
        converted_time_zone = time_zone

    # convert the time zone
    pandas_time_converted = pandas_time_localized.tz_convert(converted_time_zone)

    # resample
    resampled_pandas = pandas_time_converted.floor(freq_map[low_frequency_time_axis])

    # strip the time zone
    return resampled_pandas.tz_localize(None)


def upsample(
    *,
    x: xr.DataArray,
    high_frequency_time_axis: Time,
    low_frequency_time_axis: Time,
    time_zone: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> xr.DataArray:
    start_time: np.datetime64 = np.datetime64(start_date)
    end_time: np.datetime64 = np.datetime64(end_date)
    if is_utc_map[high_frequency_time_axis]:
        start_time = pandas_timestamp_to_datetime64_utc(
            pd.Timestamp(start_date, tz=time_zone)
        )
        end_time = pandas_timestamp_to_datetime64_utc(
            pd.Timestamp(end_date, tz=time_zone)
        )

    ideal_time_range = pd.date_range(
        start=start_time,
        end=end_time,
        freq=freq_map[high_frequency_time_axis],
        tz=None,
        inclusive="both",
    )
    resampled_time = resampled_array(
        high_frequency_time_axis=high_frequency_time_axis,
        low_frequency_time_axis=low_frequency_time_axis,
        time_zone=time_zone,
        time=ideal_time_range.to_numpy(),
    )
    mapped_array = xr.DataArray(
        data=resampled_time,
        dims=[high_frequency_time_axis.value],
        coords={high_frequency_time_axis.value: ideal_time_range},
        name=low_frequency_time_axis.value,
    )
    return broadcast(x=x, mapped_coordinates=mapped_array)


def cast_type(*, x: xr.DataArray, dtype: str) -> xr.DataArray:
    """
    Cast data array to specified data type.

    Args:
        x: Input data array to cast
        dtype: Target data type string ("float64", "int64")

    Returns:
        Data array cast to specified type
    """
    data_type_dictionary = {
        "float64": np.float64,
        "int64": np.int64,
    }
    return x.astype(data_type_dictionary[dtype])


def calculate_seconds(x: xr.DataArray) -> float:
    """
    Calculate the time interval in seconds from a time series.

    Args:
        x: Input data array with time coordinate

    Returns:
        Time interval in seconds

    Raises:
        AssertionError: If frequency cannot be inferred
    """
    pd_freq_str = pd.infer_freq(x.coords[Time.TIME_5MIN_UTC.value])
    assert pd_freq_str is not None, "Frequency not found"
    offset = pd.tseries.frequencies.to_offset(pd_freq_str)
    time_delta = pd.Timedelta(offset.nanos, unit="ns")
    return time_delta.total_seconds()
