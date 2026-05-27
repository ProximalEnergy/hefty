from typing import Protocol
from warnings import WarningMessage

import pandas as pd
import xarray as xr
from core.enumerations import SensorTypeEnum

from core import models

# ================================
# Node Protocols
# ================================


class NodeProtocol(Protocol):
    def inputs(self) -> set[str]: ...


class ProjectAttributeProtocol(NodeProtocol, Protocol):
    def run(self, project: models.Project) -> xr.DataArray: ...


def project_attribute_protocol[P: ProjectAttributeProtocol](cls: type[P]) -> type[P]:
    return cls


class DeviceProtocol(NodeProtocol, Protocol):
    def device_type_ids(self) -> set[int]: ...

    def run(self, device_df: pd.DataFrame) -> xr.DataArray: ...


def device_protocol[P: DeviceProtocol](cls: type[P]) -> type[P]:
    return cls


class SensorProtocol(NodeProtocol, Protocol):
    sensor_type: SensorTypeEnum

    def run(
        self,
        *,
        tag_df: pd.DataFrame,
        data_raw: pd.DataFrame,
        sensor_to_device_map: dict[int, int],
    ) -> xr.DataArray | None:
        pass


def sensor_protocol[P: SensorProtocol](cls: type[P]) -> type[P]:
    return cls


# ================================
# Other Protocols
# ================================


class ArgProtocol[T](Protocol):
    def input_name(self) -> str | None: ...

    def extract(self, dataset: xr.Dataset) -> T: ...


class PlanProtocol(Protocol):
    def trim(self, outputs: set[str], delete: bool = True) -> set[str]: ...

    def outputs(self) -> list[str]: ...


def plan_protocol[P: PlanProtocol](cls: type[P]) -> type[P]:
    return cls


class SchemaProtocol[P: PlanProtocol](Protocol):
    def run(self, dataset: xr.Dataset, plan: P) -> xr.Dataset: ...

    def full_plan(self) -> P: ...


def schema_protocol[P: SchemaProtocol](cls: type[P]) -> type[P]:
    return cls


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


def observer_protocol[P: ObserverProtocol](cls: type[P]) -> type[P]:
    return cls
