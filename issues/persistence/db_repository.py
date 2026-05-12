"""Database-backed issue persistence implementation."""

import datetime
import logging
from typing import Any, Literal
from uuid import UUID

from core.database import with_db
from core.db_query import DbQuery, OutputType
from core.dependencies import get_project_name_short
from sqlalchemy.orm import Session

from core import crud
from issues.models.issue_candidate import IssueCandidate, IssueIdentity
from issues.models.persistence_models import IssueRecord
from issues.persistence.matcher import candidate_identity, issue_identity
from issues.persistence.repository import IssuePersistenceResult

LOGGER = logging.getLogger(__name__)


class DbIssueRepository:
    """Persist issues and state updates in project and operational tables."""

    def get_issue_category_id(self, *, category_name: str) -> int:
        """Resolve issue category id from operational issue categories table."""
        LOGGER.info(
            "\t\tResolving issue category id for category_name=%s",
            category_name,
        )
        rows = (
            crud.operational.issue_categories.get_issue_categories(
                name_longs=[category_name]
            ).get(output_type=OutputType.SQLALCHEMY, schema="operational")
            or []
        )
        if not rows:
            msg = f"Missing issue category: {category_name}"
            raise ValueError(msg)
        category_id = int(rows[0].issue_category_id)
        LOGGER.info(
            "\t\t\tResolved issue category id=%s for category_name=%s",
            category_id,
            category_name,
        )
        return category_id

    def apply_candidates(
        self,
        *,
        project_id: str,
        run_time: datetime.datetime,
        candidates: list[IssueCandidate],
        reconciliation_window_minutes: int | None = None,
    ) -> IssuePersistenceResult:
        """Create, match, and resolve issue episodes for one project run."""
        project_schema = _resolve_project_schema_from_id(project_id=project_id)
        LOGGER.info(
            "\t\tApplying issue candidates for project_id=%s schema=%s run_time=%s "
            "candidate_count=%s",
            project_id,
            project_schema,
            run_time.isoformat(),
            len(candidates),
        )
        is_reconciliation_run = reconciliation_window_minutes is not None
        scoped_issues = self._load_scoped_issues(
            project_schema=project_schema,
            run_time=run_time,
            reconciliation_window_minutes=reconciliation_window_minutes,
        )
        issues_by_identity = _group_issues_by_identity(issues=scoped_issues)
        open_state_id = self._get_state_id(state_name="Open")
        resolved_state_id = self._get_state_id(state_name="Resolved")
        opened_count = 0
        matched_count = 0
        resolved_count = 0
        deleted_count = 0

        with with_db(schema=project_schema) as db:
            for candidate in candidates:
                identity = candidate_identity(candidate=candidate)
                existing_issues = issues_by_identity.pop(identity, [])
                if existing_issues:
                    existing = _select_issue_to_keep(issues=existing_issues)
                    earliest_time_start = min(
                        candidate.time_start,
                        *(issue.time_start for issue in existing_issues),
                    )
                    LOGGER.info(
                        "\t\t\tMatched existing issue_id=%s for identity=%s",
                        existing.issue_id,
                        _identity_to_log(identity=identity),
                    )
                    matched_count += 1
                    _execute_scalar_write(
                        query=crud.project.issues.update_issue(
                            issue_id=existing.issue_id,
                            values={
                                "time_start": earliest_time_start,
                                "time_end": None,
                                "detector_metadata": dict(candidate.detector_metadata),
                            },
                        ),
                        db=db,
                    )
                    if existing.time_end is not None:
                        _execute_scalar_write(
                            query=crud.project.issues.create_issue_update(
                                issue_update={
                                    "issue_id": existing.issue_id,
                                    "issue_state_id": open_state_id,
                                    "state_time_start": run_time,
                                    "state_changed_source": candidate.detector_name,
                                },
                            ),
                            db=db,
                        )
                    for duplicate in existing_issues:
                        if duplicate.issue_id == existing.issue_id:
                            continue
                        deleted_count += int(
                            _execute_scalar_write(
                                query=crud.project.issues.query_delete_issue(
                                    issue_id=duplicate.issue_id,
                                ),
                                db=db,
                            )
                        )
                    continue

                opened_count += 1
                created = _execute_scalar_returning(
                    query=crud.project.issues.create_issue(
                        issue={
                            "device_id": identity.device_id,
                            "tag_id": identity.tag_id,
                            "issue_category_id": identity.issue_category_id,
                            "time_start": candidate.time_start,
                            "time_end": None,
                            "detector_metadata": dict(candidate.detector_metadata),
                        },
                    ),
                    db=db,
                )
                created_issue_id = int(created["issue_id"])
                LOGGER.info(
                    "\t\tOpened new issue_id=%s for identity=%s",
                    created_issue_id,
                    _identity_to_log(identity=identity),
                )
                _execute_scalar_write(
                    query=crud.project.issues.create_issue_update(
                        issue_update={
                            "issue_id": created_issue_id,
                            "issue_state_id": open_state_id,
                            "state_time_start": run_time,
                            "state_changed_source": candidate.detector_name,
                        },
                    ),
                    db=db,
                )

            for identity, remaining_issues in issues_by_identity.items():
                if is_reconciliation_run:
                    for issue in remaining_issues:
                        LOGGER.info(
                            "\t\tDeleting erroneous issue_id=%s for identity=%s",
                            issue.issue_id,
                            _identity_to_log(identity=identity),
                        )
                        deleted_count += int(
                            _execute_scalar_write(
                                query=crud.project.issues.query_delete_issue(
                                    issue_id=issue.issue_id,
                                ),
                                db=db,
                            )
                        )
                    continue

                for active_issue in remaining_issues:
                    resolved_count += 1
                    LOGGER.info(
                        "\t\tResolving issue_id=%s for identity=%s",
                        active_issue.issue_id,
                        _identity_to_log(identity=identity),
                    )
                    _execute_scalar_write(
                        query=crud.project.issues.close_issue(
                            issue_id=active_issue.issue_id,
                            time_end=run_time,
                        ),
                        db=db,
                    )
                    source = str(
                        active_issue.detector_metadata.get(
                            "detector_name",
                            "issues_orchestrator",
                        )
                    )
                    _execute_scalar_write(
                        query=crud.project.issues.create_issue_update(
                            issue_update={
                                "issue_id": active_issue.issue_id,
                                "issue_state_id": resolved_state_id,
                                "state_time_start": run_time,
                                "state_changed_source": source,
                            },
                        ),
                        db=db,
                    )

            db.commit()
            LOGGER.info(
                "\t\tCommitted lifecycle updates for project_id=%s opened=%s matched=%s "
                "resolved=%s deleted=%s",
                project_id,
                opened_count,
                matched_count,
                resolved_count,
                deleted_count,
            )

        active_count = self._count_active_issues(project_schema=project_schema)
        LOGGER.info(
            "\t\tIssue persistence summary project_id=%s active_count=%s",
            project_id,
            active_count,
        )
        return IssuePersistenceResult(
            opened_count=opened_count,
            matched_count=matched_count,
            resolved_count=resolved_count,
            active_count=active_count,
        )

    def _get_state_id(self, *, state_name: str) -> int:
        LOGGER.info("\t\tResolving issue state id for state_name=%s", state_name)
        rows = (
            crud.operational.issue_states.get_issue_states(name_longs=[state_name]).get(
                output_type=OutputType.SQLALCHEMY, schema="operational"
            )
            or []
        )
        if not rows:
            msg = f"Missing issue state: {state_name}"
            raise ValueError(msg)
        state_id = int(rows[0].issue_state_id)
        LOGGER.info(
            "\t\t\tResolved issue state id=%s for state_name=%s",
            state_id,
            state_name,
        )
        return state_id

    def _count_active_issues(self, *, project_schema: str) -> int:
        active = crud.project.issues.get_issues(open_only=True).get(
            output_type=OutputType.POLARS,
            schema=project_schema,
        )
        count = int(active.height)
        LOGGER.info(
            "\t\tCounted active issues schema=%s count=%s",
            project_schema,
            count,
        )
        return count

    def _load_scoped_issues(
        self,
        *,
        project_schema: str,
        run_time: datetime.datetime,
        reconciliation_window_minutes: int | None,
    ) -> list[IssueRecord]:
        if reconciliation_window_minutes is None:
            rows = crud.project.issues.get_issues(open_only=True).get(
                output_type=OutputType.POLARS,
                schema=project_schema,
            )
        else:
            window_start = run_time - datetime.timedelta(
                minutes=reconciliation_window_minutes
            )
            rows = crud.project.issues.get_issues_open_in_window(
                time_start=window_start,
                time_end=run_time,
            ).get(
                output_type=OutputType.POLARS,
                schema=project_schema,
            )

        if rows.is_empty():
            LOGGER.info("\t\tNo scoped issues found for schema=%s", project_schema)
            return []

        issues = [_issue_record_from_row(row=row) for row in rows.iter_rows(named=True)]
        LOGGER.info(
            "\t\tLoaded scoped issues for schema=%s count=%s",
            project_schema,
            len(issues),
        )
        return issues


def _issue_record_from_row(*, row: dict) -> IssueRecord:
    detector_metadata = row.get("detector_metadata")
    return IssueRecord(
        issue_id=int(row["issue_id"]),
        device_id=int(row["device_id"]),
        tag_id=_coerce_optional_int(raw=row["tag_id"]),
        issue_category_id=int(row["issue_category_id"]),
        time_start=row["time_start"],
        time_end=row["time_end"],
        detector_metadata=(
            detector_metadata if isinstance(detector_metadata, dict) else {}
        ),
    )


def _execute_scalar_write(*, query: DbQuery[Any, Literal[True]], db: Session) -> bool:
    result = query.get(executor=db, output_type=OutputType.SQLALCHEMY)
    return result is not None


def _execute_scalar_returning(
    *,
    query: DbQuery[Any, Literal[True]],
    db: Session,
) -> Any:
    result = query.get(executor=db, output_type=OutputType.SQLALCHEMY)
    if result is None:
        msg = "Expected write query to return a row"
        raise ValueError(msg)
    return result


def _group_issues_by_identity(
    *,
    issues: list[IssueRecord],
) -> dict[IssueIdentity, list[IssueRecord]]:
    grouped: dict[IssueIdentity, list[IssueRecord]] = {}
    for issue in issues:
        grouped.setdefault(issue_identity(issue=issue), []).append(issue)
    return grouped


def _select_issue_to_keep(*, issues: list[IssueRecord]) -> IssueRecord:
    return sorted(
        issues,
        key=lambda issue: (
            issue.time_start,
            issue.issue_id,
        ),
    )[0]


def _coerce_optional_int(*, raw: object) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float | str):
        return int(raw)
    return int(str(raw))


def _resolve_project_schema_from_id(*, project_id: str) -> str:
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return project_id

    name_short = get_project_name_short(project_id=project_uuid)
    if name_short is None:
        msg = f"Could not resolve project_name_short for project_id={project_id}"
        raise ValueError(msg)
    return name_short


def _identity_to_log(*, identity: IssueIdentity) -> str:
    """Serialize issue identity for compact structured logging."""
    return (
        f"device_id={identity.device_id},tag_id={identity.tag_id},"
        f"issue_category_id={identity.issue_category_id}"
    )
