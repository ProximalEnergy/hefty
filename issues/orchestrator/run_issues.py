"""Top-level orchestration entrypoint for multi-project issues runs."""

import datetime
import importlib.metadata
import logging
import sys
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

if __package__ is None or __package__ == "":
    repo_root = Path(__file__).resolve().parents[2]
    core_src = repo_root / "core" / "src"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(core_src) not in sys.path:
        sys.path.insert(0, str(core_src))

from core.db_query import OutputType
from core.enumerations import ProjectStatusType, ProjectTypeEnum

from core import crud
from issues.logging_utils import setup_logging
from issues.orchestrator.context_builder import load_project_coordinates
from issues.orchestrator.run_project import (
    ProjectIssueRunSummary,
    resolve_project_name_short,
    run_project_issues,
)

LOGGER = logging.getLogger(__name__)

_BACKFILL_DAY_WINDOW_MINUTES = 24 * 60


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
            project_type_ids=[ProjectTypeEnum.PV, ProjectTypeEnum.PVS],
        ).get(output_type=OutputType.SQLALCHEMY)
        or []
    )
    ids = [str(project.project_id) for project in projects]
    return sorted(ids)


def run_issues_for_projects(
    *,
    project_ids: list[str] | None = None,
    run_time: datetime.datetime | None = None,
    issue_category_ids: list[int] | None = None,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
) -> list[ProjectIssueRunSummary]:
    """Run the automated issues pipeline across selected projects."""
    LOGGER.info(
        "Starting issues run orchestration with core_version=%s",
        get_core_package_version(),
    )
    projects = project_ids or discover_project_ids()
    if start is not None and end is not None:
        return run_issues_backfill_for_projects(
            project_ids=projects,
            issue_category_ids=issue_category_ids,
            start=start,
            end=end,
        )

    now = run_time or datetime.datetime.now(datetime.UTC)
    LOGGER.info(
        "Resolved project scope for issues run",
        extra={
            "project_count": len(projects),
            "run_time": now.isoformat(),
            "issue_category_ids": issue_category_ids,
        },
    )
    results = _run_projects_once(
        project_ids=projects,
        run_time=now,
        issue_category_ids=issue_category_ids,
    )
    LOGGER.info("Completed issues run orchestration")
    return results


def run_issues_backfill_for_projects(
    *,
    project_ids: list[str],
    issue_category_ids: list[int] | None,
    start: datetime.date,
    end: datetime.date,
) -> list[ProjectIssueRunSummary]:
    """Run issues backfill by day across selected projects.

    Each calendar day (project-local) runs once with a 24-hour evaluation window
    ending at the next local midnight (``run_time`` in UTC), so telemetry and
    detectors cover the full day, not a single hour.

    Args:
        project_ids: Projects to run.
        issue_category_ids: Optional category ids to filter detector runs.
        start: Inclusive local-date start boundary.
        end: Inclusive local-date end boundary.
    """
    if start > end:
        msg = "start must be less than or equal to end"
        raise ValueError(msg)

    results: list[ProjectIssueRunSummary] = []
    day_count = (end - start).days + 1
    LOGGER.info(
        "Starting issues backfill",
        extra={
            "project_count": len(project_ids),
            "day_count": day_count,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "issue_category_ids": issue_category_ids,
        },
    )
    for project_id in project_ids:
        time_zone = _resolve_project_time_zone(project_id=project_id)
        LOGGER.info(
            "Backfill project scope",
            extra={
                "project_id": project_id,
                "time_zone": time_zone,
            },
        )
        project_schema = resolve_project_name_short(project_id=project_id)
        project_coordinates = load_project_coordinates(
            project_name_short=project_schema,
        )
        LOGGER.info(
            "Backfill project coordinates loaded",
            extra={
                "project_id": project_id,
                "has_coordinates": project_coordinates[0] is not None,
            },
        )
        for local_day in _iter_dates(start=start, end=end):
            local_next_midnight = datetime.datetime.combine(
                local_day + datetime.timedelta(days=1),
                datetime.time.min,
                tzinfo=ZoneInfo(time_zone),
            )
            utc_run_time = local_next_midnight.astimezone(datetime.UTC)
            LOGGER.info(
                "\tBackfill calendar day=%s project_id=%s run_time_utc=%s "
                "window_minutes=%s",
                local_day.isoformat(),
                project_id,
                utc_run_time.isoformat(),
                _BACKFILL_DAY_WINDOW_MINUTES,
            )
            results.extend(
                _run_projects_once(
                    project_ids=[project_id],
                    run_time=utc_run_time,
                    issue_category_ids=issue_category_ids,
                    evaluation_window_minutes_override=_BACKFILL_DAY_WINDOW_MINUTES,
                    project_coordinates=project_coordinates,
                )
            )
    LOGGER.info("Completed issues backfill orchestration")
    return results


def _run_projects_once(
    *,
    project_ids: list[str],
    run_time: datetime.datetime,
    issue_category_ids: list[int] | None,
    evaluation_window_minutes_override: int | None = None,
    project_coordinates: tuple[float | None, float | None] | None = None,
) -> list[ProjectIssueRunSummary]:
    """Run a single time-slice across project ids."""
    results: list[ProjectIssueRunSummary] = []
    for project_id in project_ids:
        LOGGER.info("\tRunning issues pipeline for project_id=%s", project_id)
        try:
            project_summary = run_project_issues(
                project_id=project_id,
                run_time=run_time,
                issue_category_ids=issue_category_ids,
                evaluation_window_minutes_override=(
                    evaluation_window_minutes_override
                ),
                project_coordinates=project_coordinates,
            )
            results.append(project_summary)
        except Exception as error:
            LOGGER.error(
                "\t\tError running issues pipeline for project_id=%s: %s",
                project_id,
                error,
            )
    return results


def _resolve_project_time_zone(*, project_id: str) -> str:
    """Resolve project timezone, defaulting to UTC when unavailable."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        projects_query = crud.operational.projects.get_projects(
            name_shorts=[project_id],
        )
    else:
        projects_query = crud.operational.projects.get_projects(
            project_ids=[project_uuid],
        )
    projects = (
        projects_query.get(
            output_type=OutputType.SQLALCHEMY,
        )
        or []
    )
    if not projects:
        LOGGER.warning(
            "Missing project row for timezone lookup project_id=%s",
            project_id,
        )
        return "UTC"
    return str(projects[0].time_zone or "UTC")


def _iter_dates(
    *,
    start: datetime.date,
    end: datetime.date,
) -> list[datetime.date]:
    """Build an inclusive date range."""
    day_count = (end - start).days + 1
    return [start + datetime.timedelta(days=offset) for offset in range(day_count)]


def main_orchestrator() -> None:
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
    main_orchestrator()
