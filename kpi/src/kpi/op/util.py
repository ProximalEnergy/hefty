from typing import Any

import pandas as pd
import xarray as xr
from kpi.base.context import get_context
from kpi.base.enumeration import TimeCoords
from kpi.base.exception import DatasetAccessError, MissingDataError
from kpi.domain.util import is_empty


def assign_var(
    dataset: xr.Dataset,
    field_name: str,
    value: Any,
    exc: type[Exception] = MissingDataError,
) -> None:
    value = xr.DataArray(value)
    if is_empty(value):
        raise exc(f"Data array for {field_name} is empty")
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

    UTC time coordinates use project ``time_zone`` so bounds match the local
    calendar. ``date_local`` is clipped with an inclusive slice through the last
    calendar day before ``end_date``. Variables without time dimensions are
    unchanged. Idempotent for a dataset whose attrs match its coordinates.
    """
    context = get_context(dataset)
    start_a = context.start_tz_aware.normalize()
    end_a = context.end_tz_aware.normalize()

    out = dataset

    for time_coord in TimeCoords:
        if time_coord.value not in out.dims:
            continue

        if time_coord == TimeCoords.DATE_LOCAL:
            start_d = pd.Timestamp(start_a.date())
            end_d = pd.Timestamp(end_a.date())
            last_inclusive = end_d - pd.Timedelta(days=1)
            out = out.sel({time_coord.value: slice(start_d, last_inclusive)})
            continue

        start_utc = start_a.tz_convert("UTC").tz_localize(None)
        end_utc = end_a.tz_convert("UTC").tz_localize(None)
        t = out.coords[time_coord.value]
        time_index = pd.DatetimeIndex(pd.to_datetime(t.values))
        mask = (time_index >= start_utc) & (time_index < end_utc)
        out = out.isel({time_coord.value: mask})

    return out


def tidy(dataset: xr.Dataset) -> xr.Dataset:
    return exclusive_end_date(tidy_coords(dataset))
