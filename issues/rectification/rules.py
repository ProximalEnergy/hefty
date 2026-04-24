"""Rectification rules for candidate suppression and deduping."""

from issues.models.issue_candidate import IssueCandidate, IssueIdentity


def deduplicate_candidates(
    *,
    candidates: list[IssueCandidate],
) -> list[IssueCandidate]:
    """Keep one candidate per identity with earliest start time."""
    by_identity: dict[IssueIdentity, IssueCandidate] = {}
    for candidate in candidates:
        existing = by_identity.get(candidate.identity)
        if existing is None or candidate.time_start < existing.time_start:
            by_identity[candidate.identity] = candidate
    return list(by_identity.values())
