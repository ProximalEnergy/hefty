"""Rectification engine for detector candidates."""

from collections.abc import Callable

from issues.models.issue_candidate import IssueCandidate
from issues.rectification.rules import deduplicate_candidates

CandidateRule = Callable[[list[IssueCandidate]], list[IssueCandidate]]


class IssueRectificationEngine:
    """Apply ordered rules to produce persistable issue candidates."""

    def __init__(
        self,
        *,
        rules: tuple[CandidateRule, ...] | None = None,
    ) -> None:
        self._rules = rules or (
            lambda candidates: deduplicate_candidates(candidates=candidates),
        )

    def rectify(
        self,
        *,
        candidates: list[IssueCandidate],
    ) -> list[IssueCandidate]:
        """Apply rectification rules and return final candidates."""
        final = candidates
        for rule in self._rules:
            final = rule(final)
        return final
