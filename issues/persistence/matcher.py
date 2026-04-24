"""Matching helpers for linking candidates to active issues."""

from issues.models.issue_candidate import IssueCandidate, IssueIdentity
from issues.models.persistence_models import IssueRecord


def candidate_identity(*, candidate: IssueCandidate) -> IssueIdentity:
    """Return business identity key for a candidate."""
    return candidate.identity


def issue_identity(*, issue: IssueRecord) -> IssueIdentity:
    """Return business identity key for an issue record."""
    return IssueIdentity(
        device_id=issue.device_id,
        tag_id=issue.tag_id,
        issue_category_id=issue.issue_category_id,
    )


def index_active_issues(
    *,
    issues: list[IssueRecord],
) -> dict[IssueIdentity, IssueRecord]:
    """Build identity index of active (time_end is null) issue episodes."""
    indexed: dict[IssueIdentity, IssueRecord] = {}
    for issue in issues:
        if issue.time_end is not None:
            continue
        indexed[issue_identity(issue=issue)] = issue
    return indexed
