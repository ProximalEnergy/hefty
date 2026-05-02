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


class CalcProtocol(NodeProtocol, Protocol):
    def run(self, dataset: xr.Dataset) -> xr.DataArray: ...


class ProjectAttributeProtocol(NodeProtocol, Protocol):
    def run(self, project: models.Project) -> xr.DataArray: ...


class DeviceProtocol(NodeProtocol, Protocol):
    def device_type_ids(self) -> set[int]: ...

    def run(self, device_df: pd.DataFrame) -> xr.DataArray: ...


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


# ================================
# Other Protocols
# ================================


class PlanProtocol(Protocol):
    def trim(self, outputs: set[str], delete: bool = True) -> set[str]: ...

    def outputs(self) -> list[str]: ...


class SchemaProtocol[P: PlanProtocol](Protocol):
    def run(self, dataset: xr.Dataset, plan: P) -> xr.Dataset: ...

    def full_plan(self) -> P: ...


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
