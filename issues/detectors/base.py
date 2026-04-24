"""Detector interface for issue modules."""

from typing import Protocol

from issues.models.detector_context import DetectorContext
from issues.models.issue_candidate import IssueCandidate


class IssueDetector(Protocol):
    """Contract all issue detectors must satisfy."""

    name: str

    def detect(
        self,
        *,
        context: DetectorContext,
    ) -> list[IssueCandidate]:
        """Return normalized issue candidates for the detector."""
