"""Persistence records for issue storage."""

import datetime
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IssueRecord:
    """Current issue-episode record (issues table equivalent)."""

    issue_id: int
    device_id: int
    tag_id: int | None
    issue_category_id: int
    time_start: datetime.datetime
    time_end: datetime.datetime | None
    detector_metadata: dict[str, Any]


@dataclass(frozen=True)
class IssueUpdateRecord:
    """State transition record (issue_updates table equivalent)."""

    issue_update_id: int
    issue_id: int
    issue_state_id: int
    state_time_start: datetime.datetime
    state_changed_source: str


@dataclass(frozen=True)
class IssueCategoryRecord:
    """Issue category lookup row."""

    issue_category_id: int
    name_long: str


@dataclass(frozen=True)
class IssueStateRecord:
    """Issue state lookup row."""

    issue_state_id: int
    name_long: str
