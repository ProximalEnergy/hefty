"""MkDocs hooks: expose griffe_runtime helpers to mkdocstrings Jinja."""

from __future__ import annotations

from typing import Any

from kpi.doc.field import doc_markdown_field
from kpi.doc.griffe_runtime import runtime_object
from kpi.doc.registration import register_doc_renderers
from mkdocstrings_handlers.python._internal.handler import PythonHandler


def on_startup(*_args: object, **_kwargs: object) -> None:
    """Register Jinja globals before mkdocstrings renders."""
    register_doc_renderers()
    _patch_python_handler_jinja_globals()


def _patch_python_handler_jinja_globals() -> None:
    if getattr(PythonHandler, "_kpi_griffe_runtime_globals", False):
        return

    _orig = PythonHandler.update_env

    def update_env(self, config: Any) -> None:
        _orig(self, config)
        self.env.globals["doc_markdown_field"] = doc_markdown_field
        self.env.globals["runtime_object"] = runtime_object

    PythonHandler.update_env = update_env  # type: ignore[method-assign]
    PythonHandler._kpi_griffe_runtime_globals = True  # type: ignore[attr-defined]
