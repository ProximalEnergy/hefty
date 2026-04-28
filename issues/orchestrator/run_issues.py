"""Top-level orchestration entrypoint for multi-project issues runs."""

import datetime
import importlib.metadata
import logging
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    repo_root = Path(__file__).resolve().parents[2]
    core_src = repo_root / "core" / "src"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(core_src) not in sys.path:
        sys.path.insert(0, str(core_src))

from core.db_query import OutputType
from core.enumerations import ProjectStatusType, ProjectType

from core import crud
from issues.logging_utils import setup_logging
from issues.orchestrator.run_project import ProjectIssueRunSummary, run_project_issues

LOGGER = logging.getLogger(__name__)


def get_core_package_version() -> str:
    """Read the installed core package version for runtime diagnostics."""
    try:
        return importlib.metadata.version("core")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def discover_project_ids() -> list[str]:
    """Read active project ids from operational.projects via core CRUD."""
    projects = (
        crud.operational.projects.get_projects(
            project_status_type_ids=[ProjectStatusType.ACTIVE],
            project_type_ids=[ProjectType.PV, ProjectType.PVS],
        ).get(output_type=OutputType.SQLALCHEMY)
        or []
    )
    ids = [str(project.project_id) for project in projects]
    return sorted(ids)


def run_issues_for_projects(
    *,
    project_ids: list[str] | None = None,
    run_time: datetime.datetime | None = None,
) -> list[ProjectIssueRunSummary]:
    """Run the automated issues pipeline across selected projects."""
    LOGGER.info(
        "Starting issues run orchestration with core_version=%s",
        get_core_package_version(),
    )
    projects = project_ids or discover_project_ids()
    now = run_time or datetime.datetime.now(datetime.UTC)
    LOGGER.info(
        "Resolved project scope for issues run",
        extra={
            "project_count": len(projects),
            "run_time": now.isoformat(),
        },
    )
    results: list[ProjectIssueRunSummary] = []
    for project_id in projects:
        LOGGER.info("\tRunning issues pipeline for project_id=%s", project_id)
        try:
            project_summary = run_project_issues(
                project_id=project_id,
                run_time=now,
            )
            results.append(project_summary)
        except Exception as e:
            LOGGER.error(
                "\t\tError running issues pipeline for project_id=%s: %s", project_id, e
            )
    LOGGER.info("Completed issues run orchestration")
    return results


def main() -> None:
    """CLI entrypoint for issues runs."""
    setup_logging(file_path=__file__)
    summaries = run_issues_for_projects()
    active_projects = [summary for summary in summaries if summary.active_count > 0]
    LOGGER.info(
        "Issues run finished with %s projects and %s active projects",
        len(summaries),
        len(active_projects),
    )


if __name__ == "__main__":
    main()
