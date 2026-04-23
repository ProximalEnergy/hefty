import inspect
from collections.abc import Callable
from typing import Any

import xarray as xr
from kpi.base.protocol import CalcProtocol
from kpi.op.field import Field, MakeField
from kpi.op.transform.input import InputType, Optional, Required


def required(field: Field[Any]) -> xr.DataArray:
    return Required(field.name)  # type: ignore


def optional(field: Field[Any]) -> xr.DataArray | None:
    return Optional(field.name)  # type: ignore


MethodFn = Callable[..., xr.DataArray]


def extract_input_mapping(fn: MethodFn) -> dict[str, InputType]:
    """Extract param name -> field name for parameters whose default is Input."""
    mapping: dict[str, InputType] = {}
    for name, param in inspect.signature(fn).parameters.items():
        if param.default is inspect.Parameter.empty:
            msg = f"{fn.__name__}: parameter {name!r} must have an InputType default"
            raise TypeError(msg)
        if not isinstance(param.default, InputType):
            msg = f"{fn.__name__}: parameter {name!r} default must be InputType"
            raise TypeError(msg)
        mapping[name] = param.default
    return mapping


class MethodCalc:
    def __init__(
        self,
        *,
        fn: MethodFn,
        inputs_map: dict[str, InputType],
    ) -> None:
        self._fn = fn
        self._inputs_map = inputs_map

    def inputs(self) -> set[str]:
        return set[str](input_type.name for input_type in self._inputs_map.values())

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        inputs = {}
        for name, input_type in self._inputs_map.items():
            value = input_type.get(dataset)
            inputs[name] = value
        return self._fn(**inputs)


def method_calc(fn: MethodFn) -> Field[CalcProtocol]:
    return Field[CalcProtocol](
        MethodCalc(
            fn=fn,
            inputs_map=extract_input_mapping(fn),
        ),
        name=fn.__name__,
        doc=fn.__doc__,
    )


calc_field = MakeField[CalcProtocol].infer_doc
