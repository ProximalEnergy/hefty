"""Orchestration entrypoints for issues processing runs."""

from issues.orchestrator.run_issues import discover_project_ids, run_issues_for_projects

__all__ = ["discover_project_ids", "run_issues_for_projects"]
