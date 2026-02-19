from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    ContextManager,
    Protocol,
    Self,
)

import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from core.models import Project
from kpi_pipeline.base.enums import Aggregation, DataType, Time
from typing_extensions import runtime_checkable

if TYPE_CHECKING:
    from kpi_pipeline.base.models import ContextModel


class ObserverProtocol(Protocol):
    ignore_errors: tuple[type[Exception], ...]

    def with_scope(self, *, scope: str | None = None) -> ContextManager[None]: ...
    def with_project(self, *, project_name_short: str) -> ContextManager[None]: ...
    def watch(self, *, var: str | None = None) -> ContextManager[None]: ...
    def log(self, *, message: str) -> None: ...


@runtime_checkable
class ProcessProtocol(Protocol):
    def __call__(
        self,
        *,
        x: xr.DataArray,
        context: "ContextModel",
    ) -> xr.DataArray: ...


@runtime_checkable
class CalcProtocol(Protocol):
    output_dtype: DataType

    def __call__(
        self,
        *,
        dataset: xr.Dataset,
        context: "ContextModel",
    ) -> xr.DataArray: ...

    def expected_inputs(self) -> list[str]: ...


class ActionProtocol[T](Protocol):
    def __call__(
        self,
        *,
        dataset: xr.Dataset,
        context: "ContextModel",
        observer: ObserverProtocol,
    ) -> T: ...

    def nominal_outputs(self) -> list[str]: ...

    @property
    def pass_through(self) -> bool: ...

    def expected_inputs(
        self,
        *,
        outputs: list[str] = [],
    ) -> list[str]:
        """Results in the required inputs to produce the outputs"""
        ...

    def trim(self, *, outputs: list[str] = []) -> Self:
        """A new transform that only produces the outputs_to_receive."""
        ...


@runtime_checkable
class SchemaProtocol[T, K](Protocol):
    _registry: ClassVar[dict[str, K]]

    @classmethod
    def export(cls, scope: str | None = None) -> ActionProtocol[T]:
        """Exports the schema to an Action/Transform"""
        ...

    @classmethod
    def _ignore_attribute_name(cls, attr_name: str) -> bool:
        """Checks to see if attribute name should be ignored in registry"""
        ...

    @classmethod
    def _check_valid_attribute_value(cls, attr_name: str, attr_value: K) -> None:
        """
        When creating a schema, check if the user defined attribute is valid (e.g. a Field)
        Throws an error if the attribute is not valid.
        """
        ...


class TransformProtocol(ActionProtocol[xr.Dataset], Protocol): ...


class DeviceManagerProtocol(Protocol):
    def __init__(self, *, project: Project): ...

    def get_devices(self) -> pd.DataFrame: ...

    def download_coords(self) -> dict[str, tuple]: ...


class CoordCombinerProtocol(Protocol):
    def group(
        self, x: xr.DataArray
    ) -> xr.core.groupby.DataArrayGroupBy | xr.DataArray: ...

    def dim(self) -> list[str]:
        """
        The string representation of the dimensions to aggregate across.
        For use with aggregating methods like .mean(dim=...) or .sum(dim=...)
        """
        ...

    def get_high_res_time_axis(self) -> Time:
        """
        Gets the string reprsentation of the high resolution time axis.
        Throws an error if it doesn't exist.
        """
        ...

    def get_low_res_time_axis(self) -> Time: ...

    def get_child_device_axis(self) -> DeviceType: ...

    def get_parent_device_axis(self) -> DeviceType: ...

    def agg(
        self,
        x: xr.DataArray,
        agg: Aggregation,
        **kwargs: Any,
    ) -> xr.DataArray: ...

    def broadcast(self, x: xr.DataArray) -> xr.DataArray: ...


class DataDownloadModelProtocol(Protocol):
    dtype: DataType
    scale: float | None
    offset: float | None
    project_level: bool


class ScaleOffsetProtocol(Protocol):
    scale: float | None
    offset: float | None


class DownloaderProtocol[T: DataDownloadModelProtocol](Protocol):
    @classmethod
    def from_download(cls, map: dict[str, T], context: "ContextModel") -> Self: ...

    def data_array(self, model: T) -> xr.DataArray: ...


class Implements[P]:
    @classmethod
    def decorator(cls, _cls: type[P]) -> type[P]:
        return _cls
