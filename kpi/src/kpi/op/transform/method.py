import inspect
from collections.abc import Callable
from typing import Protocol

import xarray as xr
from kpi.base.protocol import (
    ArgProtocol,
    CalcProtocol,
    calc_protocol,
)
from kpi.doc.reference import method_doc_header
from kpi.op.field import Field

MethodFn = Callable[..., xr.DataArray]


@calc_protocol
class MethodCalc:
    def __init__(
        self,
        fn: MethodFn,
        args: tuple[ArgProtocol, ...],
        kwargs: dict[str, ArgProtocol],
    ) -> None:
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

        signature = inspect.signature(fn)

        try:
            signature.bind(*args, **kwargs)
        except TypeError as e:
            raise TypeError(
                f"Failed to bind arguments to function {fn.__name__}: {e}"
            ) from e

    def inputs(self) -> set[str]:
        arg_inputs = {arg.input_name for arg in self.args if arg.input_name is not None}
        kwarg_inputs = {
            kwarg.input_name
            for kwarg in self.kwargs.values()
            if kwarg.input_name is not None
        }
        return arg_inputs | kwarg_inputs

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        return self.fn(
            *[arg.extract(dataset) for arg in self.args],
            **{name: value.extract(dataset) for name, value in self.kwargs.items()},
        )


class CalcFieldFactoryProtocol(Protocol):
    def __call__(
        self, *args: ArgProtocol, **kwargs: ArgProtocol
    ) -> Field[CalcProtocol]: ...


def calc_field(
    fn: MethodFn, doc_header: str | None = None
) -> CalcFieldFactoryProtocol:
    if doc_header is None:
        doc_header = method_doc_header(fn=fn)

    def _calc_field(*args: ArgProtocol, **kwargs: ArgProtocol) -> Field[CalcProtocol]:
        return Field[CalcProtocol](
            MethodCalc(fn=fn, args=args, kwargs=kwargs),
            doc_header=doc_header,
        )

    return _calc_field

