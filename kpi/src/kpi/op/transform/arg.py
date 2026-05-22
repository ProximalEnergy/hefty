from abc import ABC, abstractmethod
from typing import Any

import pandas as pd
import xarray as xr
from kpi.base.context import get_context
from kpi.base.enumeration import NEW_NAME, TIME_DESCRIPTOR, TimeCoord
from kpi.base.exception import DatasetAccessError
from kpi.base.protocol import arg_protocol
from kpi.op.field import Field


class ArgType(ABC):
    """
    A nominal type in order to dynamically check
    whether an object is an instance of a subclass of `ArgType`.
    """

    @abstractmethod
    def extract(self, dataset: xr.Dataset) -> Any: ...


class _DataArrayArgType:
    def __init__(self, field: Field[Any]) -> None:
        self.field = field

    @property
    def input_name(self) -> str:
        return self.field.name


@arg_protocol
class Required(_DataArrayArgType, ArgType):
    def extract(self, dataset: xr.Dataset) -> xr.DataArray:
        try:
            return dataset[self.field.name]
        except KeyError as e:
            raise DatasetAccessError(str(e)) from e


@arg_protocol
class Optional(_DataArrayArgType, ArgType):
    def extract(self, dataset: xr.Dataset) -> xr.DataArray | None:
        try:
            return dataset[self.field.name]
        except KeyError:
            return None


@arg_protocol
class TimeZone(ArgType):
    input_name = None

    def extract(self, dataset: xr.Dataset) -> str:
        return get_context(dataset).time_zone


@arg_protocol
class TimeCoordArg(ArgType):
    input_name = None

    def __init__(self, time_coord: TimeCoord) -> None:
        self.time_coord = time_coord

    def extract(self, dataset: xr.Dataset) -> pd.DatetimeIndex:
        tz = "UTC"
        if not TIME_DESCRIPTOR[self.time_coord].utc:
            tz = get_context(dataset).time_zone
        return pd.DatetimeIndex(dataset.coords[self.time_coord.value].values, tz=tz)


@arg_protocol
class Constant[T](ArgType):
    input_name = None

    def __init__(self, value: T) -> None:
        self.value = value

    def extract(self, dataset: xr.Dataset) -> T:
        _ = dataset
        return self.value


@arg_protocol
class Grouper(_DataArrayArgType, ArgType):
    def extract(self, dataset: xr.Dataset) -> xr.DataArray:
        try:
            x = dataset[self.input_name]
            return x.rename(x.attrs[NEW_NAME])
        except KeyError as e:
            raise DatasetAccessError(str(e)) from e
