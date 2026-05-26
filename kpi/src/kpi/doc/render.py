from enum import Enum
from functools import singledispatch
from typing import Any

from pydantic import BaseModel


@singledispatch
def render_doc_value(value: Any) -> str:
    return str(value)


@render_doc_value.register(Enum)
def _(value: Enum) -> str:
    return f"*{value.name}*: {value.value}"


@render_doc_value.register(tuple)
def _(value: tuple) -> str:
    return ", ".join(render_doc_value(item) for item in value)


def markdown_table(*, values: dict[str, Any]) -> str:
    return "| Parameter | Value |\n| --- | --- |\n" + "\n".join(
        f"| `{key}` | {render_doc_value(value)} |" for key, value in values.items()
    )


def _model_doc_values(node: BaseModel) -> dict[str, Any]:
    dumped = node.model_dump(
        exclude_defaults=True, exclude_unset=True, exclude_none=True
    )
    return {key: getattr(node, key) for key in dumped}


@singledispatch
def node_doc_markdown(node: Any) -> str:
    _ = node
    return ""


@node_doc_markdown.register
def _(node: BaseModel) -> str:
    return markdown_table(values=_model_doc_values(node))
