from dataclasses import dataclass
from typing import Protocol, Self

import numpy as np
import pandas as pd
import xarray as xr
from core.enumerations import DeviceType


class DeviceTreeProtocol(Protocol):
    def parent_device_series(
        self, child_device_type: DeviceType, parent_device_type: DeviceType
    ) -> pd.Series: ...


@dataclass
class DeviceGrouper(xr.groupers.Grouper):
    from_device_axis: DeviceType
    to_device_axis: DeviceType
    device_tree: DeviceTreeProtocol
    _factorized: xr.groupers.EncodedGroups | None = None

    def _factorize(self, group: xr.DataArray) -> xr.groupers.EncodedGroups:
        parent_device_series = self.device_tree.parent_device_series(
            child_device_type=self.from_device_axis,
            parent_device_type=self.to_device_axis,
        )
        series_filtered = parent_device_series.loc[
            group.coords[self.from_device_axis.name.lower()].values
        ]
        full_index, codes_arr = np.unique(series_filtered.values, return_inverse=True)
        codes = xr.DataArray(
            codes_arr,
            dims=[self.from_device_axis.name.lower()],
            coords={self.from_device_axis.name.lower(): series_filtered.index.values},
            name=self.to_device_axis.name.lower(),
        )
        return xr.groupers.EncodedGroups(codes, pd.Index(full_index))

    def factorize(self, group) -> xr.groupers.EncodedGroups:
        if self._factorized is None:
            self._factorized = self._factorize(group)
        return self._factorized

    def reset(self) -> Self:
        return self.__class__(
            from_device_axis=self.from_device_axis,
            to_device_axis=self.to_device_axis,
            device_tree=self.device_tree,
        )
