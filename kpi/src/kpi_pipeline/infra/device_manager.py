from typing import Self

import pandas as pd
import xarray as xr
from core.crud.project.devices import get_project_devices
from core.db_query import OutputType
from core.enumerations import DeviceType
from kpi_pipeline.base.enums import (
    supported_devices,
)
from kpi_pipeline.infra.device_grouper import DeviceTreeProtocol
from pydantic import ConfigDict, validate_call

from core import models

arbitrary_types = ConfigDict(arbitrary_types_allowed=True)


class DeviceTree(DeviceTreeProtocol):
    def __init__(self, device_df: pd.DataFrame):
        self.device_df = device_df
        self._device_level_map: dict[DeviceType, int] = {}

    @classmethod
    def from_project(cls, project: models.Project) -> Self:
        devices = get_project_devices(
            device_type_ids=[DeviceType.PROJECT.value]
            + [device_type.value for device_type in supported_devices],
        ).get(schema=project.name_short, output_type=OutputType.PANDAS)
        devices_df = devices.set_index(models.Device.device_id.name)[
            [models.Device.device_id_path.name, models.Device.device_type_id.name]
        ]
        return cls(devices_df)

    @validate_call
    def device_level(self, device_type: DeviceType) -> int:
        if device_type.value in self._device_level_map:
            return self._device_level_map[device_type]
        filtered_df = self.device_df.loc[
            self.device_df.device_type_id == device_type.value
        ]
        if filtered_df.empty:
            raise ValueError(
                f"No devices found for device type {repr(device_type)} in the DeviceTree"
            )
        self._device_level_map[device_type] = int(
            filtered_df.device_id_path.str.split(".").str.len().max() - 1
        )
        return self._device_level_map[device_type]

    @validate_call
    def parent_device_series(
        self, child_device_type: DeviceType, parent_device_type: DeviceType
    ) -> pd.Series:
        parent_device_level = self.device_level(parent_device_type)
        filtered_df = (
            self.device_df.loc[
                self.device_df.device_type_id == child_device_type.value,
                models.Device.device_id_path.name,
            ]
            .str.split(".", expand=True)
            .astype(int)
        )
        if parent_device_level >= filtered_df.shape[1]:
            raise ValueError(
                f"{repr(parent_device_type)} is not a parent of {repr(child_device_type)}"
            )
        result: pd.Series = filtered_df.iloc[:, parent_device_level]
        return result

    @validate_call
    def parent_device_data_array(
        self, child_device_type: DeviceType, parent_device_type: DeviceType
    ) -> xr.DataArray:
        parent_device_series = self.parent_device_series(
            child_device_type, parent_device_type
        )
        return xr.DataArray(
            data=parent_device_series.values,
            dims=[child_device_type.name.lower()],
            coords={child_device_type.name.lower(): parent_device_series.index.values},
            name=parent_device_type.name.lower(),
        )

    def device_ids(self, device_type: DeviceType) -> list[int]:
        return self.device_df.loc[
            self.device_df.device_type_id == device_type.value
        ].index.tolist()
