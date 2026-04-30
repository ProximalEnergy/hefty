"""Database-backed issue persistence implementation."""

import datetime
import logging
from uuid import UUID

from core.database import with_db
from core.db_query import OutputType
from core.dependencies import get_project_name_short

from core import crud
from issues.models.issue_candidate import IssueCandidate, IssueIdentity
from issues.models.persistence_models import IssueRecord
from issues.persistence.matcher import candidate_identity, index_active_issues
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
        active = self._load_active_issues(project_schema=project_schema)
        open_state_id = self._get_state_id(state_name="Open")
        resolved_state_id = self._get_state_id(state_name="Resolved")
        opened_count = 0
        matched_count = 0
        resolved_count = 0
        seen_identities = set()

        with with_db(schema=project_schema) as db:
            for candidate in candidates:
                identity = candidate_identity(candidate=candidate)
                seen_identities.add(identity)
                existing = active.get(identity)
                if existing is not None:
                    LOGGER.info(
                        "\t\t\tMatched existing issue_id=%s for identity=%s",
                        existing.issue_id,
                        _identity_to_log(identity=identity),
                    )
                    matched_count += 1
                    crud.project.issues.update_issue(
                        db=db,
                        issue_id=existing.issue_id,
                        values={
                            "detector_metadata": dict(candidate.detector_metadata),
                        },
                    )
                    continue

                opened_count += 1
                created = crud.project.issues.create_issue(
                    db=db,
                    issue={
                        "device_id": identity.device_id,
                        "tag_id": identity.tag_id,
                        "issue_category_id": identity.issue_category_id,
                        "time_start": candidate.time_start,
                        "time_end": None,
                        "detector_metadata": dict(candidate.detector_metadata),
                    },
                )
                LOGGER.info(
                    "\t\tOpened new issue_id=%s for identity=%s",
                    created.issue_id,
                    _identity_to_log(identity=identity),
                )
                crud.project.issues.create_issue_update(
                    db=db,
                    issue_update={
                        "issue_id": created.issue_id,
                        "issue_state_id": open_state_id,
                        "state_time_start": run_time,
                        "state_changed_source": candidate.detector_name,
                    },
                )

            for identity, active_issue in active.items():
                if identity in seen_identities:
                    continue
                resolved_count += 1
                LOGGER.info(
                    "\t\tResolving issue_id=%s for identity=%s",
                    active_issue.issue_id,
                    _identity_to_log(identity=identity),
                )
                crud.project.issues.close_issue(
                    db=db,
                    issue_id=active_issue.issue_id,
                    time_end=run_time,
                )
                source = str(
                    active_issue.detector_metadata.get(
                        "detector_name",
                        "issues_orchestrator",
                    )
                )
                crud.project.issues.create_issue_update(
                    db=db,
                    issue_update={
                        "issue_id": active_issue.issue_id,
                        "issue_state_id": resolved_state_id,
                        "state_time_start": run_time,
                        "state_changed_source": source,
                    },
                )

            db.commit()
            LOGGER.info(
                "\t\tCommitted lifecycle updates for project_id=%s opened=%s matched=%s "
                "resolved=%s",
                project_id,
                opened_count,
                matched_count,
                resolved_count,
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

    def _load_active_issues(self, *, project_schema: str) -> dict:
        rows = crud.project.issues.get_issues(open_only=True).get(
            output_type=OutputType.POLARS,
            schema=project_schema,
        )
        if rows.is_empty():
            LOGGER.info("\t\tNo active issues found for schema=%s", project_schema)
            return {}

        issues: list[IssueRecord] = []
        for row in rows.iter_rows(named=True):
            detector_metadata = row.get("detector_metadata")
            issues.append(
                IssueRecord(
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
            )
        indexed = index_active_issues(issues=issues)
        LOGGER.info(
            "\t\tLoaded active issues for schema=%s count=%s",
            project_schema,
            len(indexed),
        )
        return indexed


def _coerce_optional_int(*, raw: object) -> int | None:
    if raw is None:
        return None
    return int(raw)


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
