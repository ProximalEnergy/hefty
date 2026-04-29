import pandas as pd
import xarray as xr
from kpi.base.enumeration import TimeCoords
from kpi.op.context import get_context


class TimeLocal:
    def inputs(self) -> set[str]:
        return set[str]()

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        utc_time = dataset.coords[TimeCoords.TIME_5MIN_UTC.value]
        tz = get_context(dataset).time_zone
        local_time = (
            pd.DatetimeIndex(utc_time.values)
            .tz_localize("UTC")
            .tz_convert(tz)
            .tz_localize(None)
        )
        return xr.DataArray(
            local_time.values,
            dims=[TimeCoords.TIME_5MIN_UTC.value],
            coords={TimeCoords.TIME_5MIN_UTC.value: utc_time},
        )


class DateLocal5m:
    """
    Local date taking into account time zone and daylight savings
    for each 5-minute UTC time stamp.
    """

    def inputs(self) -> set[str]:
        return set[str]()

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        utc_time = dataset.coords[TimeCoords.TIME_5MIN_UTC.value]
        tz = get_context(dataset).time_zone
        local_time = (
            pd.DatetimeIndex(utc_time.values)
            .tz_localize("UTC")
            .tz_convert(tz)
            .tz_localize(None)
        )
        date_local = local_time.floor("D").to_numpy()
        return xr.DataArray(
            date_local,
            dims=[TimeCoords.TIME_5MIN_UTC.value],
            coords={TimeCoords.TIME_5MIN_UTC.value: utc_time},
        )

