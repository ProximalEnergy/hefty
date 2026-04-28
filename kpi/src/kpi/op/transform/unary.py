from collections.abc import Callable
from typing import Any

import xarray as xr
from kpi.base.protocol import CalcProtocol
from kpi.op.field import Field
from kpi.op.util import select_var


class UnaryCalc:
    def __init__(self, fn: Callable[[xr.DataArray], xr.DataArray], input: str) -> None:
        self.fn = fn
        self.input = input

    def inputs(self) -> set[str]:
        return {self.input}

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        return self.fn(select_var(dataset, self.input))


def unary_field(
    fn: Callable[[xr.DataArray], xr.DataArray],
    *,
    field: Field[Any],
) -> Field[CalcProtocol]:
    return Field[CalcProtocol](UnaryCalc(fn=fn, input=field.name))


_: CalcProtocol = UnaryCalc(fn=lambda x: x, input="")
