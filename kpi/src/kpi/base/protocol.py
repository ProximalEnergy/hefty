from collections.abc import Mapping
from typing import Protocol
from warnings import WarningMessage

import pandas as pd
import xarray as xr
from core.enumerations import DeviceType, SensorType

from core import models


class HasInputsProtocol(Protocol):
    def inputs(self) -> set[str]: ...


class SchemaProtocol(Protocol):
    def field_registry(self) -> Mapping[str, HasInputsProtocol]: ...

    @property
    def plan(self) -> dict[str, set[str]]: ...

    def compile(self, outputs: set[str], *, delete: bool = True) -> set[str]: ...

    def run(self, dataset: xr.Dataset) -> xr.Dataset: ...


class SchemaClassProtocol(Protocol):
    def field_registry(self) -> Mapping[str, HasInputsProtocol]: ...

    def __call__(self) -> SchemaProtocol: ...


class CalcProtocol(Protocol):
    def inputs(self) -> set[str]: ...

    def run(self, dataset: xr.Dataset) -> xr.DataArray: ...


class ProjectAttributeProtocol(Protocol):
    def inputs(self) -> set[str]: ...

    def run(self, project: models.Project) -> xr.DataArray: ...


class DeviceAttributeProtocol(Protocol):
    device_type: DeviceType

    def inputs(self) -> set[str]: ...

    def run(self, data_raw: pd.DataFrame) -> xr.DataArray: ...


class SensorProtocol(Protocol):
    sensor_type: SensorType

    def inputs(self) -> set[str]: ...

    def run(
        self,
        *,
        tag_df: pd.DataFrame,
        data_raw: pd.DataFrame,
        sensor_to_device_map: dict[int, int],
    ) -> xr.DataArray | None:
        pass


class ObserverProtocol(Protocol):
    def handle_error(
        self, error: Exception, *, field_name: str | None = None
    ) -> None: ...

    def handle_warnings(
        self,
        warning_messages: list[WarningMessage],
        *,
        field_name: str | None = None,
    ) -> None: ...
