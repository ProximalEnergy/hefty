from dataclasses import dataclass
from typing import Self

import numpy as np
import pandas as pd
import xarray as xr

from kpi_pipeline.base.enums import Time
from kpi_pipeline.infra.utils import resampled_array


@dataclass
class TimeGrouper(xr.groupers.Grouper):
    from_time_axis: Time
    to_time_axis: Time
    time_zone: str
    _factorized: xr.groupers.EncodedGroups | None = None

    def _factorize(self, group: xr.DataArray) -> xr.groupers.EncodedGroups:
        time = group.coords[self.from_time_axis.value].values
        resampled_time = resampled_array(
            high_frequency_time_axis=self.from_time_axis,
            low_frequency_time_axis=self.to_time_axis,
            time_zone=self.time_zone,
            time=time,
        )
        codes_arr, full_index = pd.factorize(resampled_time, sort=True)
        codes = xr.DataArray(
            codes_arr,
            dims=[self.from_time_axis.value],
            coords={self.from_time_axis.value: time},
            name=self.to_time_axis.value,
        )
        return xr.groupers.EncodedGroups(codes, pd.DatetimeIndex(full_index))

    def factorize(self, group) -> xr.groupers.EncodedGroups:
        if self._factorized is None:
            self._factorized = self._factorize(group)
        return self._factorized

    def reset(self) -> Self:
        return self.__class__(
            from_time_axis=self.from_time_axis,
            to_time_axis=self.to_time_axis,
            time_zone=self.time_zone,
        )


if __name__ == "__main__":
    time = pd.date_range(start="2025-01-01", end="2025-01-03", freq="5min")
    x = xr.DataArray(
        np.random.randn(len(time)), coords={Time.TIME_5MIN_UTC.value: time}
    )
    time_zone = "America/New_York"
    grouper = TimeGrouper(
        from_time_axis=Time.TIME_5MIN_UTC,
        to_time_axis=Time.DATE_LOCAL,
        time_zone=time_zone,
    )
    x.groupby({Time.TIME_5MIN_UTC.value: grouper}).mean()
