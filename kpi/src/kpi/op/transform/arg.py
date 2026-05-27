from abc import ABC, abstractmethod
from typing import Annotated, Any, Literal

import pandas as pd
import pydantic as pyd
import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.context import get_context
from kpi.base.enumeration import NEW_NAME, TIME_DESCRIPTOR, TimeCoord
from kpi.base.exception import DatasetAccessError
from kpi.op.field import Field
from pydantic import BaseModel


class ArgAbstract[T](BaseModel, ABC):
    def input_name(self) -> str | None:
        return None

    @abstractmethod
    def extract(self, dataset: xr.Dataset) -> T:
        pass


def arg_type[T: ArgAbstract](cls: type[T]) -> type[T]:
    return cls


class _DataArrayArgType(BaseModel):
    field_name: str

    def input_name(self) -> str:
        return self.field_name


class _NoInput(BaseModel):
    def input_name(self) -> None:
        return None


@arg_type
class Required(_DataArrayArgType, ArgAbstract):
    kind: Literal["Required"] = "Required"

    def extract(self, dataset: xr.Dataset) -> xr.DataArray:
        try:
            return dataset[self.field_name]
        except KeyError as e:
            raise DatasetAccessError(str(e)) from e


def required(field: Field[Any]) -> Required:
    return Required(field_name=field.name)


@arg_type
class Optional(_DataArrayArgType, ArgAbstract):
    kind: Literal["Optional"] = "Optional"

    def extract(self, dataset: xr.Dataset) -> xr.DataArray | None:
        try:
            return dataset[self.field_name]
        except KeyError:
            return None


def optional(field: Field[Any]) -> Optional:
    return Optional(field_name=field.name)


@arg_type
class Grouper(_DataArrayArgType, ArgAbstract):
    kind: Literal["Grouper"] = "Grouper"

    def extract(self, dataset: xr.Dataset) -> xr.DataArray:
        try:
            x = dataset[self.input_name()]
            return x.rename(x.attrs[NEW_NAME])
        except KeyError as e:
            raise DatasetAccessError(str(e)) from e


def grouper(field: Field[Any]) -> Grouper:
    return Grouper(field_name=field.name)


@arg_type
class TimeZone(ArgAbstract):
    kind: Literal["TimeZone"] = "TimeZone"

    def extract(self, dataset: xr.Dataset) -> str:
        return get_context(dataset).time_zone


@arg_type
class TimeCoordArg(ArgAbstract):
    kind: Literal["TimeCoordArg"] = "TimeCoordArg"
    time_coord: TimeCoord

    def extract(self, dataset: xr.Dataset) -> pd.DatetimeIndex:
        tz = "UTC"
        if not TIME_DESCRIPTOR[self.time_coord].utc:
            tz = get_context(dataset).time_zone
        return pd.DatetimeIndex(dataset.coords[self.time_coord.value].values, tz=tz)


class _Constant[T: Any](ArgAbstract[T]):
    value: T

    def extract(self, dataset: xr.Dataset) -> T:
        _ = dataset
        return self.value


@arg_type
class Constant[T](_Constant[T]):
    kind: Literal["Constant"] = "Constant"


@arg_type
class DeviceTypeConstant(_Constant[DeviceTypeEnum]):
    kind: Literal["DeviceTypeConstant"] = "DeviceTypeConstant"


@arg_type
class TimeCoordConstant(_Constant[TimeCoord]):
    kind: Literal["TimeCoordConstant"] = "TimeCoordConstant"


ArgType = Annotated[
    Required
    | Optional
    | Grouper
    | TimeZone
    | TimeCoordArg
    | DeviceTypeConstant
    | TimeCoordConstant
    | Constant,
    pyd.Field(discriminator="kind"),
]
