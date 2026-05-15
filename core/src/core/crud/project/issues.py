import datetime
from typing import Any, Literal

import sqlalchemy as sa
from core.db_query import DbQuery
from sqlalchemy import or_
from sqlalchemy.orm import Session

from core import models


def get_maximum_issue_id(*, db: Session) -> int:
    """Return the maximum issue_id in the project issues table.

    Args:
        db: SQLAlchemy session for querying issues.
    """
    return db.scalar(sa.select(sa.func.max(models.Issue.issue_id))) or 0


def get_issue(
    *,
    issue_id: int,
) -> DbQuery[models.Issue, Literal[True]]:
    """Build a query for a single issue row by issue id.

    Args:
        issue_id: Issue id to fetch.
    """
    stmt = sa.select(models.Issue).where(models.Issue.issue_id == issue_id)
    return DbQuery(query=stmt, is_scalar=True)


def get_issues(
    *,
    issue_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
    tag_ids: list[int] | None = None,
    issue_category_ids: list[int] | None = None,
    time_start: datetime.datetime | None = None,
    time_end: datetime.datetime | None = None,
    window_start: datetime.datetime | None = None,
    window_end: datetime.datetime | None = None,
    open_only: bool = False,
) -> DbQuery[models.Issue, Literal[False]]:
    """Build a query for issue rows using optional filters.

    Args:
        issue_ids: Issue ids to include.
        device_ids: Device ids to include.
        tag_ids: Tag ids to include.
        issue_category_ids: Issue category ids to include.
        issue_state_ids: Current issue state ids to include.
        time_start: Include issues with time_start >= this timestamp.
        time_end: Include issues with time_start <= this timestamp.
        window_start: Include issues active at or after this timestamp.
        window_end: Include issues active at or before this timestamp.
        open_only: Include only unresolved issues (time_end is null).

    TODO: Add a filter for issue_state_ids by joining on issue_updates, and
    finding the most recent update for each issue.
    """
    stmt = sa.select(models.Issue)
    if issue_ids is not None:
        stmt = stmt.where(models.Issue.issue_id.in_(issue_ids))
    if device_ids is not None:
        stmt = stmt.where(models.Issue.device_id.in_(device_ids))
    if tag_ids is not None:
        stmt = stmt.where(models.Issue.tag_id.in_(tag_ids))
    if issue_category_ids is not None:
        stmt = stmt.where(models.Issue.issue_category_id.in_(issue_category_ids))
    if time_start is not None:
        stmt = stmt.where(models.Issue.time_start >= time_start)
    if time_end is not None:
        stmt = stmt.where(models.Issue.time_start <= time_end)
    if window_start is not None:
        stmt = stmt.where(
            or_(models.Issue.time_end >= window_start, models.Issue.time_end.is_(None))
        )
    if window_end is not None:
        stmt = stmt.where(models.Issue.time_start <= window_end)
    if open_only:
        stmt = stmt.where(models.Issue.time_end.is_(None))
    return DbQuery(query=stmt)


def get_issues_open_in_window(
    *,
    time_start: datetime.datetime,
    time_end: datetime.datetime,
) -> DbQuery[models.Issue, Literal[False]]:
    """Build a query for issues active at any point in a time window.

    Args:
        time_start: Inclusive start of the overlap window.
        time_end: Inclusive end of the overlap window.
    """
    stmt = sa.select(models.Issue)
    stmt = stmt.where(models.Issue.time_start <= time_end)
    stmt = stmt.where(
        or_(models.Issue.time_end >= time_start, models.Issue.time_end.is_(None))
    )
    return DbQuery(query=stmt)


def create_issue(*, issue: dict[str, Any]) -> DbQuery[Any, Literal[True]]:
    """Build an insert for a new issue row.

    Args:
        issue: Mapping of issue column values.
    """
    payload = dict(issue)
    stmt = sa.insert(models.Issue).values(payload).returning(models.Issue.issue_id)
    return DbQuery(query=stmt, is_scalar=True)


def update_issue(
    *,
    issue_id: int,
    values: dict[str, Any],
) -> DbQuery[Any, Literal[True]]:
    """Build an update for an issue row.

    Args:
        issue_id: Issue id to update.
        values: Column values to update.
    """
    if not values:
        msg = "values must not be empty"
        raise ValueError(msg)
    stmt = (
        sa.update(models.Issue)
        .where(models.Issue.issue_id == issue_id)
        .values(**values)
        .returning(models.Issue.issue_id)
        .execution_options(synchronize_session=False)
    )
    return DbQuery(query=stmt, is_scalar=True)


def close_issue(
    *,
    issue_id: int,
    time_end: datetime.datetime,
) -> DbQuery[Any, Literal[True]]:
    """Build an update that sets an issue's time_end.

    Args:
        issue_id: Issue id to close.
        time_end: Resolution timestamp.
    """
    return update_issue(issue_id=issue_id, values={"time_end": time_end})


def query_delete_issue(*, issue_id: int) -> DbQuery[Any, Literal[True]]:
    """Build a delete for an issue row.

    Args:
        issue_id: Issue id to delete.
    """
    stmt = (
        sa.delete(models.Issue)  # nosemgrep: sqlalchemy-db-crud-outside-dbquery
        .where(models.Issue.issue_id == issue_id)
        .returning(models.Issue.issue_id)
        .execution_options(synchronize_session=False)
    )
    return DbQuery(query=stmt, is_scalar=True)


def create_issue_update(
    *,
    issue_update: dict[str, Any],
) -> DbQuery[Any, Literal[True]]:
    """Build an insert for an issue update row.

    Args:
        issue_update: Mapping of issue update column values.
    """
    payload = dict(issue_update)
    stmt = (
        sa.insert(models.IssueUpdate)
        .values(payload)
        .returning(models.IssueUpdate.issue_update_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


def create_issue_updates(
    *,
    db: Session,
    issue_updates: list[dict[str, Any]],
) -> int:
    """Insert multiple issue update rows and return inserted row count.

    Args:
        db: SQLAlchemy session for the project schema.
        issue_updates: Rows to insert.
    """
    if not issue_updates:
        return 0
    stmt = sa.insert(models.IssueUpdate).values(issue_updates)
    result = db.execute(stmt)
    rowcount = getattr(result, "rowcount", None)
    return int(rowcount or 0)


def get_issue_updates(
    *,
    issue_update_ids: list[int] | None = None,
    issue_ids: list[int] | None = None,
    issue_state_ids: list[int] | None = None,
    state_time_start: datetime.datetime | None = None,
    state_time_end: datetime.datetime | None = None,
) -> DbQuery[models.IssueUpdate, Literal[False]]:
    """Build a query for issue update rows using optional filters.

    Args:
        issue_update_ids: Issue update ids to include.
        issue_ids: Issue ids to include.
        issue_state_ids: State ids to include.
        state_time_start: Include updates on/after this timestamp.
        state_time_end: Include updates on/before this timestamp.
    """
    stmt = sa.select(models.IssueUpdate)
    if issue_update_ids:
        stmt = stmt.where(models.IssueUpdate.issue_update_id.in_(issue_update_ids))
    if issue_ids:
        stmt = stmt.where(models.IssueUpdate.issue_id.in_(issue_ids))
    if issue_state_ids:
        stmt = stmt.where(models.IssueUpdate.issue_state_id.in_(issue_state_ids))
    if state_time_start is not None:
        stmt = stmt.where(models.IssueUpdate.state_time_start >= state_time_start)
    if state_time_end is not None:
        stmt = stmt.where(models.IssueUpdate.state_time_start <= state_time_end)
    return DbQuery(query=stmt)
