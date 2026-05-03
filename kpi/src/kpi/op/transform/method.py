import inspect
from collections.abc import Callable
from typing import Protocol

import xarray as xr
from kpi.base.protocol import (
    ArgProtocol,
    CalcFactoryProtocol,
    CalcProtocol,
    calc_protocol,
)
from kpi.op.field import Field

MethodFn = Callable[..., xr.DataArray]


def make_method_calc(fn: MethodFn) -> CalcFactoryProtocol:
    signature = inspect.signature(fn)

    @calc_protocol
    class _MethodCalc:
        def __init__(self, *args: ArgProtocol, **kwargs: ArgProtocol) -> None:
            self.args = args
            self.kwargs = kwargs

            try:
                signature.bind(*args, **kwargs)
            except TypeError as e:
                raise TypeError(
                    f"Failed to bind arguments to function {fn.__name__}: {e}"
                ) from e

        def inputs(self) -> set[str]:
            arg_inputs = {
                arg.input_name for arg in self.args if arg.input_name is not None
            }
            kwarg_inputs = {
                kwarg.input_name
                for kwarg in self.kwargs.values()
                if kwarg.input_name is not None
            }
            return arg_inputs | kwarg_inputs

        def run(self, dataset: xr.Dataset) -> xr.DataArray:
            return fn(
                *[arg.extract(dataset) for arg in self.args],
                **{name: value.extract(dataset) for name, value in self.kwargs.items()},
            )

    return _MethodCalc


class CalcFieldFactoryProtocol(Protocol):
    def __call__(
        self, *args: ArgProtocol, **kwargs: ArgProtocol
    ) -> Field[CalcProtocol]: ...


def calc_field(fn: MethodFn) -> CalcFieldFactoryProtocol:
    def _calc_field(*args: ArgProtocol, **kwargs: ArgProtocol) -> Field[CalcProtocol]:
        return Field[CalcProtocol](
            make_method_calc(fn)(*args, **kwargs),
        )

    return _calc_field


def method_calc(
    *args: ArgProtocol, **kwargs: ArgProtocol
) -> Callable[[MethodFn], Field[CalcProtocol]]:
    def wrap(fn: MethodFn) -> Field[CalcProtocol]:
        return calc_field(fn)(*args, **kwargs)

    return wrap
