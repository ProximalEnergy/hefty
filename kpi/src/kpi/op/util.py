from typing import Any

import pandas as pd
import xarray as xr
from kpi.base.enumeration import TimeCoords
from kpi.base.exception import DatasetAccessError, MissingDataError
from kpi.op.context import get_context


def assign_var(
    dataset: xr.Dataset,
    field_name: str,
    value: Any,
    exc: type[Exception] = MissingDataError,
) -> None:
    if value is None:
        raise exc(f"Data array for {field_name} is None")
    value = xr.DataArray(value)
    if value.size == 0:
        raise exc(f"Data array for {field_name} is empty")
    if value.isnull().all():
        raise exc(f"Data array for {field_name} is all null")
    dataset[field_name] = value


def select_var(dataset: xr.Dataset, field_name: str) -> xr.DataArray:
    try:
        return dataset[field_name]
    except KeyError as e:
        raise DatasetAccessError(str(e)) from e


def select_optional(dataset: xr.Dataset, field_name: str) -> xr.DataArray | None:
    try:
        return dataset[field_name]
    except KeyError:
        return None


def tidy_coords(dataset: xr.Dataset) -> xr.Dataset:
    used_coords = {
        coord_name
        for data_var in dataset.data_vars.values()
        for coord_name in data_var.coords
    }
    unused_coords = [name for name in dataset.coords if name not in used_coords]
    return dataset.drop_vars(unused_coords)


def exclusive_end_date(dataset: xr.Dataset) -> xr.Dataset:
    """Clip to ``[start_date, end_date)`` on each time dimension.

    ``time_5min_utc`` uses project ``time_zone`` so bounds match the local
    calendar. ``date_local`` is clipped with an inclusive slice through the last
    calendar day before ``end_date``. Variables without those dimensions are
    unchanged. Idempotent for a dataset whose attrs match its coordinates.
    """
    context = get_context(dataset)
    start_a = context.start_tz_aware.normalize()
    end_a = context.end_tz_aware.normalize()

    out = dataset

    if TimeCoords.TIME_5MIN_UTC.value in dataset.dims:
        start_utc = start_a.tz_convert("UTC").tz_localize(None)
        end_utc = end_a.tz_convert("UTC").tz_localize(None)
        t = out.coords[TimeCoords.TIME_5MIN_UTC.value]
        time_index = pd.DatetimeIndex(pd.to_datetime(t.values))
        mask = (time_index >= start_utc) & (time_index < end_utc)
        out = out.isel({TimeCoords.TIME_5MIN_UTC.value: mask})

    if TimeCoords.DATE_LOCAL.value in out.dims:
        start_d = pd.Timestamp(start_a.date())
        end_d = pd.Timestamp(end_a.date())
        last_inclusive = end_d - pd.Timedelta(days=1)
        out = out.sel({TimeCoords.DATE_LOCAL.value: slice(start_d, last_inclusive)})

    return out


def tidy(dataset: xr.Dataset) -> xr.Dataset:
    return exclusive_end_date(tidy_coords(dataset))
