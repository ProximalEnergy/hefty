"""Repository contract for issue persistence backends."""

import datetime
from dataclasses import dataclass
from typing import Protocol

from issues.models.issue_candidate import IssueCandidate


@dataclass(frozen=True)
class IssuePersistenceResult:
    """Summary metrics returned by persistence operations."""

    opened_count: int
    matched_count: int
    resolved_count: int
    active_count: int


class IssueRepository(Protocol):
    """Persistence abstraction for issue state and updates logging."""

    def get_issue_category_id(
        self,
        *,
        category_name: str,
    ) -> int:
        """Resolve category name to id."""

    def apply_candidates(
        self,
        *,
        project_id: str,
        run_time: datetime.datetime,
        candidates: list[IssueCandidate],
    ) -> IssuePersistenceResult:
        """Create, match, and resolve issue episodes for this run."""
