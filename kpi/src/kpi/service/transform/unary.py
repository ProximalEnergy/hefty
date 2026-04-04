from collections.abc import Callable

import xarray as xr
from kpi.base.protocol import CalcProtocol
from kpi.service.field import Field
from kpi.service.util import select_var


class UnaryCalc:
    def __init__(self, fn: Callable[[xr.DataArray], xr.DataArray], name: str) -> None:
        self.fn = fn
        self.name = name

    def inputs(self) -> set[str]:
        return {self.name}

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        return self.fn(select_var(dataset, self.name))


def unary_field(
    fn: Callable[[xr.DataArray], xr.DataArray], name: str
) -> Field[UnaryCalc]:
    return Field[UnaryCalc](UnaryCalc(fn=fn, name=name))


_: CalcProtocol = UnaryCalc(fn=lambda x: x, name="")
