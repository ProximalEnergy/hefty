import inspect
from collections.abc import Callable
from typing import Literal, Protocol

import xarray as xr
from kpi.base.protocol import ArgProtocol
from kpi.doc.reference import method_doc_header
from kpi.op.field import Field
from kpi.op.node import NodeModel, node_type
from kpi.op.transform.arg import ArgType
from pydantic import ImportString, model_validator

MethodFn = Callable[..., xr.DataArray]


@node_type
class MethodCalc(NodeModel):
    kind: Literal["MethodCalc"] = "MethodCalc"

    fn: ImportString
    args: tuple[ArgType, ...]
    keyword_args: dict[str, ArgType]

    @model_validator(mode="after")
    def validate_args(self) -> "MethodCalc":
        signature = inspect.signature(self.fn)
        signature.bind(*self.args, **self.keyword_args)
        return self

    def inputs(self) -> set[str]:
        arg_inputs = {
            input_name
            for arg in self.args
            if (input_name := arg.input_name()) is not None
        }
        kwarg_inputs = {
            input_name
            for kwarg in self.keyword_args.values()
            if (input_name := kwarg.input_name()) is not None
        }
        return arg_inputs | kwarg_inputs

    def run(self, dataset: xr.Dataset) -> xr.DataArray:
        return self.fn(
            *[arg.extract(dataset) for arg in self.args],
            **{
                name: value.extract(dataset)
                for name, value in self.keyword_args.items()
            },
        )


class CalcFieldFactoryProtocol(Protocol):
    def __call__(
        self, *args: ArgProtocol, **kwargs: ArgProtocol
    ) -> Field[MethodCalc]: ...


def calc_field(fn: MethodFn, doc_header: str | None = None) -> CalcFieldFactoryProtocol:
    if doc_header is None:
        doc_header = method_doc_header(fn=fn)

    def _calc_field(*args: ArgProtocol, **kwargs: ArgProtocol) -> Field[MethodCalc]:
        return Field[MethodCalc](
            MethodCalc(fn=fn, args=args, keyword_args=kwargs),
            doc_header=doc_header,
        )

    return _calc_field
