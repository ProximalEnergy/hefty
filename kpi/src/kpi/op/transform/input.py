from abc import ABC, abstractmethod
from typing import Any

import xarray as xr
from kpi.base.exception import DatasetAccessError
from kpi.op.field import Field


class InputType(ABC):
    def __init__(self, field: Field[Any]) -> None:
        self.name = field.name

    @abstractmethod
    def extract(self, ds: xr.Dataset) -> xr.DataArray | None: ...


class Required(InputType):
    def extract(self, ds: xr.Dataset) -> xr.DataArray:
        try:
            return ds[self.name]
        except KeyError as e:
            raise DatasetAccessError(str(e)) from e


class Optional(InputType):
    def extract(self, ds: xr.Dataset) -> xr.DataArray | None:
        try:
            return ds[self.name]
        except KeyError:
            return None
