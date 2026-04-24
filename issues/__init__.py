"""Issues detection pipeline package."""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
core_src = repo_root / "core" / "src"
if str(core_src) not in sys.path:
    sys.path.insert(0, str(core_src))

from issues.orchestrator.run_issues import discover_project_ids, run_issues_for_projects

__all__ = ["discover_project_ids", "run_issues_for_projects"]
