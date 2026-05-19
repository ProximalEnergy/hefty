"""Top-level orchestration entrypoint for multi-project issues runs."""

import datetime
import importlib.metadata
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

if __package__ is None or __package__ == "":
    repo_root = Path(__file__).resolve().parents[2]
    core_src = repo_root / "core" / "src"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(core_src) not in sys.path:
        sys.path.insert(0, str(core_src))

from core.crud.operational import projects as operational_projects
from core.db_query import OutputType
from core.enumerations import ProjectStatusType, ProjectTypeEnum

from issues.logging_utils import setup_logging
from issues.orchestrator.context_builder import _extract_coordinates
from issues.orchestrator.run_project import ProjectIssueRunSummary, run_project_issues

LOGGER = logging.getLogger(__name__)

_BACKFILL_DAY_WINDOW_MINUTES = 24 * 60


@dataclass(frozen=True)
class ProjectRunMetadata:
    """Project metadata reused across an issues orchestration run."""

    name_short: str
    time_zone: str
    coordinates: tuple[float | None, float | None]


def _floor_to_five_minute_boundary(
    *,
    value: datetime.datetime,
) -> datetime.datetime:
    """Floor a timezone-aware datetime to its prior 5-minute boundary."""
    floored_minute = value.minute - (value.minute % 5)
    return value.replace(
        minute=floored_minute,
        second=0,
        microsecond=0,
    )


def get_core_package_version() -> str:
    """Read the installed core package version for runtime diagnostics."""
    try:
        return importlib.metadata.version("core")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def discover_project_ids() -> list[str]:
    """Read active project ids from operational.projects via core CRUD."""
    projects = (
        operational_projects.get_projects(
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

    if run_time is None:
        raw_now = datetime.datetime.now(datetime.UTC)
        now = _floor_to_five_minute_boundary(value=raw_now)
    else:
        raw_now = run_time
        now = run_time
    LOGGER.info(
        "Resolved project scope for issues run",
        extra={
            "project_count": len(projects),
            "raw_run_time": raw_now.isoformat(),
            "run_time": now.isoformat(),
            "issue_category_ids": issue_category_ids,
        },
    )
    results = _run_default_project_scope(
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
    metadata_by_identifier = _load_project_metadata_by_identifier(
        project_ids=project_ids
    )
    for project_id in project_ids:
        metadata = metadata_by_identifier.get(project_id)
        time_zone = _project_time_zone(metadata=metadata, project_id=project_id)
        LOGGER.info(
            "Backfill project scope",
            extra={
                "project_id": project_id,
                "time_zone": time_zone,
            },
        )
        results.extend(
            _run_backfill_for_project_days(
                project_id=project_id,
                issue_category_ids=issue_category_ids,
                start=start,
                end=end,
                time_zone=time_zone,
                project_metadata=metadata,
            )
        )
    LOGGER.info("Completed issues backfill orchestration")
    return results


def run_local_midnight_backfill_for_projects(
    *,
    project_ids: list[str] | None = None,
    run_time: datetime.datetime | None = None,
    issue_category_ids: list[int] | None = None,
) -> list[ProjectIssueRunSummary]:
    """Run yesterday's 24-hour backfill for projects at local midnight.

    Args:
        project_ids: Optional project scope. Defaults to all discovered projects.
        run_time: UTC anchor time. Defaults to the current UTC time.
        issue_category_ids: Optional category ids to filter detector runs.
    """
    projects = project_ids or discover_project_ids()
    now = run_time or datetime.datetime.now(datetime.UTC)
    now = _as_utc_datetime(value=now)
    metadata_by_identifier = _load_project_metadata_by_identifier(project_ids=projects)

    results: list[ProjectIssueRunSummary] = []
    LOGGER.info(
        "Starting local-midnight issues backfill scan",
        extra={
            "project_count": len(projects),
            "run_time": now.isoformat(),
        },
    )
    for project_id in projects:
        metadata = metadata_by_identifier.get(project_id)
        time_zone = _project_time_zone(metadata=metadata, project_id=project_id)
        local_now = now.astimezone(ZoneInfo(time_zone))
        if local_now.hour != 0:
            LOGGER.info(
                "\tSkipping project_id=%s because local time is %s",
                project_id,
                local_now.isoformat(),
            )
            continue

        local_day = local_now.date() - datetime.timedelta(days=1)
        LOGGER.info(
            "\tRunning local-midnight backfill project_id=%s local_day=%s",
            project_id,
            local_day.isoformat(),
        )
        results.extend(
            _run_local_midnight_backfill_for_project(
                project_id=project_id,
                run_time=run_time or now,
                issue_category_ids=issue_category_ids,
                time_zone=time_zone,
                project_metadata=metadata,
            )
        )
    LOGGER.info("Completed local-midnight issues backfill scan")
    return results


def _run_default_project_scope(
    *,
    project_ids: list[str],
    run_time: datetime.datetime,
    issue_category_ids: list[int] | None,
) -> list[ProjectIssueRunSummary]:
    """Run normal projects and local-midnight backfills for the default path."""
    metadata_by_identifier = _load_project_metadata_by_identifier(
        project_ids=project_ids
    )
    normal_project_ids: list[str] = []
    results: list[ProjectIssueRunSummary] = []
    for project_id in project_ids:
        metadata = metadata_by_identifier.get(project_id)
        time_zone = _project_time_zone(metadata=metadata, project_id=project_id)
        if _time_zone_is_at_local_midnight(time_zone=time_zone, run_time=run_time):
            results.extend(
                _run_local_midnight_backfill_for_project(
                    project_id=project_id,
                    run_time=run_time,
                    issue_category_ids=issue_category_ids,
                    time_zone=time_zone,
                    project_metadata=metadata,
                )
            )
        else:
            normal_project_ids.append(project_id)

    if normal_project_ids:
        results.extend(
            _run_projects_once(
                project_ids=normal_project_ids,
                run_time=run_time,
                issue_category_ids=issue_category_ids,
                project_metadata_by_identifier=metadata_by_identifier,
            )
        )
    return results


def _run_local_midnight_backfill_for_project(
    *,
    project_id: str,
    run_time: datetime.datetime,
    issue_category_ids: list[int] | None,
    time_zone: str,
    project_metadata: ProjectRunMetadata | None,
) -> list[ProjectIssueRunSummary]:
    """Run yesterday's backfill for one project using known project metadata."""
    now = _as_utc_datetime(value=run_time)
    local_now = now.astimezone(ZoneInfo(time_zone))
    local_day = local_now.date() - datetime.timedelta(days=1)
    LOGGER.info(
        "\tRunning local-midnight backfill project_id=%s local_day=%s",
        project_id,
        local_day.isoformat(),
    )
    return _run_backfill_for_project_days(
        project_id=project_id,
        issue_category_ids=issue_category_ids,
        start=local_day,
        end=local_day,
        time_zone=time_zone,
        project_metadata=project_metadata,
    )


def _run_backfill_for_project_days(
    *,
    project_id: str,
    issue_category_ids: list[int] | None,
    start: datetime.date,
    end: datetime.date,
    time_zone: str,
    project_metadata: ProjectRunMetadata | None,
) -> list[ProjectIssueRunSummary]:
    """Run 24-hour backfill windows for one project over local dates."""
    results: list[ProjectIssueRunSummary] = []
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
                project_metadata_by_identifier=(
                    {project_id: project_metadata}
                    if project_metadata is not None
                    else None
                ),
            )
        )
    return results


def _time_zone_is_at_local_midnight(
    *,
    time_zone: str,
    run_time: datetime.datetime,
) -> bool:
    """Return whether the timezone-local hour is midnight for a run."""
    local_run_time = _as_utc_datetime(value=run_time).astimezone(ZoneInfo(time_zone))
    return local_run_time.hour == 0


def _load_project_metadata_by_identifier(
    *,
    project_ids: list[str],
) -> dict[str, ProjectRunMetadata]:
    """Load reusable project metadata for ids or name_shorts in bulk."""
    uuid_ids: list[UUID] = []
    name_shorts: list[str] = []
    for project_id in project_ids:
        try:
            uuid_ids.append(UUID(project_id))
        except ValueError:
            name_shorts.append(project_id)

    project_rows: list[Any] = []
    if uuid_ids:
        project_rows.extend(
            operational_projects.get_projects(project_ids=uuid_ids).get(
                output_type=OutputType.SQLALCHEMY
            )
            or []
        )
    if name_shorts:
        project_rows.extend(
            operational_projects.get_projects(name_shorts=name_shorts).get(
                output_type=OutputType.SQLALCHEMY
            )
            or []
        )

    projects_by_identifier: dict[str, ProjectRunMetadata] = {}
    for project in project_rows:
        metadata = _project_metadata_from_row(project=project)
        projects_by_identifier[str(project.project_id)] = metadata
        if project.name_short is None:
            raise ValueError(f"Project {project.project_id} missing name_short")
        projects_by_identifier[str(project.name_short)] = metadata
    return projects_by_identifier


def _project_metadata_from_row(*, project: Any) -> ProjectRunMetadata:
    """Build issues run metadata from an operational project row."""
    coordinates = _extract_coordinates(raw=project.point)
    if coordinates[0] is None or coordinates[1] is None:
        LOGGER.warning(
            "Project coordinates missing for project_name_short=%s",
            project.name_short,
        )
    return ProjectRunMetadata(
        name_short=str(project.name_short),
        time_zone=str(project.time_zone or "UTC"),
        coordinates=coordinates,
    )


def _project_time_zone(
    *,
    metadata: ProjectRunMetadata | None,
    project_id: str,
) -> str:
    """Return the project's timezone, defaulting to UTC when unavailable."""
    if metadata is None:
        LOGGER.warning(
            "Missing project row for timezone lookup project_id=%s",
            project_id,
        )
        return "UTC"
    return metadata.time_zone


def _as_utc_datetime(*, value: datetime.datetime) -> datetime.datetime:
    """Normalize datetimes to UTC for local-time comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.UTC)
    return value.astimezone(datetime.UTC)


def _run_projects_once(
    *,
    project_ids: list[str],
    run_time: datetime.datetime,
    issue_category_ids: list[int] | None,
    evaluation_window_minutes_override: int | None = None,
    project_coordinates: tuple[float | None, float | None] | None = None,
    project_metadata_by_identifier: dict[str, ProjectRunMetadata] | None = None,
) -> list[ProjectIssueRunSummary]:
    """Run a single time-slice across project ids."""
    results: list[ProjectIssueRunSummary] = []
    for project_id in project_ids:
        LOGGER.info("\tRunning issues pipeline for project_id=%s", project_id)
        project_metadata = (project_metadata_by_identifier or {}).get(project_id)
        resolved_coordinates = (
            project_metadata.coordinates
            if project_metadata is not None
            else project_coordinates
        )
        try:
            project_summary = run_project_issues(
                project_id=project_id,
                run_time=run_time,
                issue_category_ids=issue_category_ids,
                evaluation_window_minutes_override=(evaluation_window_minutes_override),
                project_name_short=(
                    project_metadata.name_short
                    if project_metadata is not None
                    else None
                ),
                project_coordinates=resolved_coordinates,
            )
            results.append(project_summary)
        except Exception as error:
            LOGGER.error(
                "\t\tError running issues pipeline for project_id=%s: %s",
                project_id,
                error,
            )
    return results


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
