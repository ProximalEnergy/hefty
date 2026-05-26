from collections.abc import Callable
from typing import Any

from kpi.op.field import FieldRef


def doc_link(name: str, module: str, qualname: str) -> str:
    return f"[`{name}`][{module}.{qualname}]"


def doc_link_field_ref(field_ref: FieldRef) -> str:
    return doc_link(field_ref.name, field_ref.module, field_ref.qualname)


def method_doc_header(*, fn: Callable[..., Any]) -> str:
    link = doc_link(fn.__name__, fn.__module__, fn.__qualname__)
    return f"Calls {link}."
