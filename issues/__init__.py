"""Issues detection pipeline package."""

import sys
from pathlib import Path
from typing import Any

repo_root = Path(__file__).resolve().parents[1]
core_src = repo_root / "core" / "src"
if core_src.exists() and str(core_src) not in sys.path:
    sys.path.insert(0, str(core_src))

__all__ = ["discover_project_ids", "run_issues_for_projects"]


def __getattr__(name: str) -> Any:
    """Lazily expose orchestrator helpers after runtime env is configured."""
    if name not in __all__:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)

    from issues.orchestrator.run_issues import (  # noqa: PLC0415
        discover_project_ids,
        run_issues_for_projects,
    )

    exports = {
        "discover_project_ids": discover_project_ids,
        "run_issues_for_projects": run_issues_for_projects,
    }
    return exports[name]
