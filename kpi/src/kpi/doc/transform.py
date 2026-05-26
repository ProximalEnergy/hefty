import inspect
from typing import Any

from kpi.doc.reference import doc_link, doc_link_field_ref
from kpi.doc.render import node_doc_markdown, render_doc_value
from kpi.op.transform.arg import (
    Constant,
    Grouper,
    Optional,
    Required,
    TimeCoordArg,
    TimeZone,
)
from kpi.op.transform.method import MethodCalc, MethodFn


def doc_link_method(*, fn: MethodFn) -> str:
    return doc_link(name=fn.__name__, module=fn.__module__, qualname=fn.__qualname__)


def _markdown_table_cell(*, text: str) -> str:
    """Escape cell text so it is safe inside a Markdown pipe table."""
    return text.replace("|", "\\|").replace("\n", " ")


def _field_arg_doc(*, arg: Required | Optional | Grouper, label: str) -> str:
    return f"*({label})* {doc_link_field_ref(arg.field_ref)}"


@render_doc_value.register(Required)
def _(arg: Required) -> str:
    return _field_arg_doc(arg=arg, label="required")


@render_doc_value.register(Optional)
def _(arg: Optional) -> str:
    return _field_arg_doc(arg=arg, label="optional")


@render_doc_value.register
def _(_arg: TimeZone) -> str:
    return "Context.time_zone"


@render_doc_value.register
def _(arg: TimeCoordArg) -> str:
    return arg.time_coord.value


@render_doc_value.register(Constant)
def _(arg: Constant[Any]) -> str:
    return str(arg.value)


@render_doc_value.register(Grouper)
def _(arg: Grouper) -> str:
    return _field_arg_doc(arg=arg, label="grouper")


@node_doc_markdown.register
def _(node: MethodCalc) -> str:
    sig = inspect.signature(node.fn)
    bound = sig.bind(*node.args, **node.kwargs)
    rows = "\n".join(
        f"| `{name}` | {_markdown_table_cell(text=render_doc_value(arg))} |"
        for name, arg in bound.arguments.items()
    )
    table = f"| Parameter | Source |\n| --- | --- |\n{rows}\n" if rows else ""
    return f"\n\n{table}" if table else ""
