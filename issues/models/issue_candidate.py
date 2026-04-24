"""Normalized candidate model emitted by detectors."""

import datetime
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IssueIdentity:
    """Business identity used for matching issue episodes."""

    device_id: int
    tag_id: int | None
    issue_category_id: int


@dataclass(frozen=True)
class IssueCandidate:
    """Detector output consumed by rectification and persistence layers."""

    project_id: str
    detector_name: str
    identity: IssueIdentity
    time_start: datetime.datetime
    detector_metadata: dict[str, Any]
