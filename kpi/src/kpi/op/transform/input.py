from abc import ABC, abstractmethod
from typing import Any, Self

import xarray as xr
from kpi.base.exception import DatasetAccessError
from kpi.op.field import Field
from pydantic import GetCoreSchemaHandler
from pydantic_core import PydanticCustomError, core_schema


class InputType(ABC):
    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def get(self, ds: xr.Dataset) -> xr.DataArray | None: ...

    @classmethod
    def _from_name(cls, name: str) -> Self:
        return cls(name)

    @classmethod
    def _validate(cls, value: Any) -> Self:
        if isinstance(value, cls):
            return value
        if isinstance(value, Field):
            return cls._from_name(value.name)
        if isinstance(value, str):
            return cls._from_name(value)
        raise PydanticCustomError(
            "input_type",
            "{class_name} must be an instance, field, or string name",
            {"class_name": cls.__name__},
        )

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        del source_type, handler
        return core_schema.no_info_plain_validator_function(cls._validate)


class Required(InputType):
    def get(self, ds: xr.Dataset) -> xr.DataArray:
        try:
            return ds[self.name]
        except KeyError as e:
            raise DatasetAccessError(str(e)) from e


class Optional(InputType):
    def get(self, ds: xr.Dataset) -> xr.DataArray | None:
        try:
            return ds[self.name]
        except KeyError:
            return None
