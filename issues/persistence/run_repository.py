"""Repository factory for issues persistence backend."""

from issues.persistence.db_repository import DbIssueRepository
from issues.persistence.repository import IssueRepository


def get_issue_repository(*, project_name_short: str) -> IssueRepository:
    """Build the issues persistence repository.

    Args:
        project_name_short: Project schema name for future repository options.
    """
    _ = project_name_short
    return DbIssueRepository()


def build_issue_repository(*, project_name_short: str) -> IssueRepository:
    """Compatibility alias for historical call sites."""
    return get_issue_repository(project_name_short=project_name_short)
