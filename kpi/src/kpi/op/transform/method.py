import inspect
from collections.abc import Callable

import xarray as xr
from kpi.base.protocol import CalcProtocol
from kpi.op.field import Field
from kpi.op.transform.input import InputType

MethodFn = Callable[..., xr.DataArray]


def validate_input_mapping(
    fn: MethodFn,
    *,
    inputs_map: dict[str, InputType],
) -> None:
    signature = inspect.signature(fn)
    params = signature.parameters

    for name, input_type in inputs_map.items():
        if name not in params:
            msg = f"{fn.__name__}: input {name!r} is not a parameter"
            raise TypeError(msg)
        if not isinstance(input_type, InputType):
            msg = f"{fn.__name__}: input {name!r} default must be InputType"  # type: ignore
            raise TypeError(msg)

    for name, param in params.items():
        if param.default is not inspect.Parameter.empty:
            msg = f"{fn.__name__}: parameter {name!r} must not have a default"
            raise TypeError(msg)
        if name not in inputs_map:
            msg = f"{fn.__name__}: parameter {name!r} must have an input"
            raise TypeError(msg)


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
            value = input_type.extract(dataset)
            inputs[name] = value
        return self._fn(**inputs)


def method_calc(**inputs_map: InputType) -> Callable[[MethodFn], Field[CalcProtocol]]:
    def wrap(fn: MethodFn) -> Field[CalcProtocol]:
        validate_input_mapping(fn, inputs_map=inputs_map)
        return Field[CalcProtocol](
            MethodCalc(
                fn=fn,
                inputs_map=inputs_map,
            ),
        )

    return wrap
