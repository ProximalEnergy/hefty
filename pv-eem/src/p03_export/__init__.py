from collections.abc import Callable
from importlib import import_module
from typing import Any, cast

from p03_export.s02_to_file import (
    export_to_file as export_to_file,
)


def plot(*, results: Any) -> Any:
    """Import Plotly export only when explicitly requested."""
    _plot = cast(
        Callable[..., Any],
        import_module("p03_export.s03_to_plotly").plot_results_to_plotly,
    )

    return _plot(results=results)
