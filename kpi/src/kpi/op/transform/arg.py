from typing import Any, Literal

import pandas as pd
import xarray as xr
from kpi.base.context import get_context
from kpi.base.enumeration import NEW_NAME, TIME_DESCRIPTOR, TimeCoord
from kpi.base.exception import DatasetAccessError
from kpi.base.protocol import arg_protocol
from kpi.op.field import Field, FieldRef
from pydantic import BaseModel


class _DataArrayArgType(BaseModel):
    field_ref: FieldRef

    def input_name(self) -> str:
        return self.field_ref.name


class _NoInput(BaseModel):
    def input_name(self) -> None:
        return None


@arg_protocol
class Required(_DataArrayArgType):
    kind: Literal["Required"] = "Required"

    def extract(self, dataset: xr.Dataset) -> xr.DataArray:
        try:
            return dataset[self.field_ref.name]
        except KeyError as e:
            raise DatasetAccessError(str(e)) from e


def required(field: Field[Any]) -> Required:
    return Required(field_ref=field.ref)


@arg_protocol
class Optional(_DataArrayArgType):
    kind: Literal["Optional"] = "Optional"

    def extract(self, dataset: xr.Dataset) -> xr.DataArray | None:
        try:
            return dataset[self.field_ref.name]
        except KeyError:
            return None


def optional(field: Field[Any]) -> Optional:
    return Optional(field_ref=field.ref)


@arg_protocol
class Grouper(_DataArrayArgType):
    kind: Literal["Grouper"] = "Grouper"

    def extract(self, dataset: xr.Dataset) -> xr.DataArray:
        try:
            x = dataset[self.input_name()]
            return x.rename(x.attrs[NEW_NAME])
        except KeyError as e:
            raise DatasetAccessError(str(e)) from e


def grouper(field: Field[Any]) -> Grouper:
    return Grouper(field_ref=field.ref)


@arg_protocol
class TimeZone(_NoInput):
    kind: Literal["TimeZone"] = "TimeZone"

    def extract(self, dataset: xr.Dataset) -> str:
        return get_context(dataset).time_zone


@arg_protocol
class TimeCoordArg(_NoInput):
    kind: Literal["TimeCoordArg"] = "TimeCoordArg"
    time_coord: TimeCoord

    def extract(self, dataset: xr.Dataset) -> pd.DatetimeIndex:
        tz = "UTC"
        if not TIME_DESCRIPTOR[self.time_coord].utc:
            tz = get_context(dataset).time_zone
        return pd.DatetimeIndex(dataset.coords[self.time_coord.value].values, tz=tz)


@arg_protocol
class Constant[T](_NoInput):
    kind: Literal["Constant"] = "Constant"
    value: T

    def extract(self, dataset: xr.Dataset) -> T:
        _ = dataset
        return self.value
