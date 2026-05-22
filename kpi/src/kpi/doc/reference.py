from collections.abc import Callable
from typing import Any


def doc_link(*, name: str, module: str, qualname: str) -> str:
    return f"[`{name}`][{module}.{qualname}]"


def method_doc_header(*, fn: Callable[..., Any]) -> str:
    link = doc_link(name=fn.__name__, module=fn.__module__, qualname=fn.__qualname__)
    return f"Calls {link}."
