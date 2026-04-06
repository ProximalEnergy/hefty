import inspect
from collections.abc import Callable
from typing import Any

import xarray as xr
from kpi.service.field import Field
from kpi.service.util import select_optional, select_var


class InputType:
    def __init__(self, name: str, optional: bool = False) -> None:
        self.name = name
        self.optional = optional


def Input(field: Field[Any]) -> xr.DataArray:
    return InputType(field.name)  # type: ignore


def Optional(field: Field[Any]) -> xr.DataArray | None:
    return InputType(field.name, optional=True)  # type: ignore


def extract_input_mapping(fn: Callable[..., Any]) -> dict[str, InputType]:
    """Extract param name -> field name for parameters whose default is InputField."""
    mapping: dict[str, InputType] = {}
    for name, param in inspect.signature(fn).parameters.items():
        if param.default is not inspect.Parameter.empty and isinstance(
            param.default, InputType
        ):
            mapping[name] = param.default
    return mapping


class MethodCalc:
    def __init__(
        self,
        *,
        fn: Callable[[], xr.DataArray],
        inputs_map: dict[str, InputType],
    ) -> None:
        self._fn = fn
        self._inputs_map = inputs_map

    def inputs(self) -> set[str]:
        return set[str](input_type.name for input_type in self._inputs_map.values())

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        inputs = {}
        for name, input_type in self._inputs_map.items():
            value = None
            if input_type.optional:
                value = select_optional(dataset, input_type.name)
            else:
                value = select_var(dataset, input_type.name)
            inputs[name] = value
        return self._fn(**inputs)


def method_calc(fn: Callable[[], xr.DataArray]) -> Field[MethodCalc]:
    return Field[MethodCalc](
        MethodCalc(
            fn=fn,
            inputs_map=extract_input_mapping(fn),
        ),
        name=fn.__name__,
    )
