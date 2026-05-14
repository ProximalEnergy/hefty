from typing import Literal

import sqlalchemy as sa
from core.db_query import DbQuery

from core import models


def get_issue_state(
    *,
    issue_state_id: int,
) -> DbQuery[models.IssueState, Literal[True]]:
    """Build a query for a single issue state by id.

    Args:
        issue_state_id: Issue state id to fetch.
    """
    stmt = sa.select(models.IssueState).where(
        models.IssueState.issue_state_id == issue_state_id
    )
    return DbQuery(query=stmt, is_scalar=True)


def get_issue_states(
    *,
    issue_state_ids: list[int] | None = None,
    name_longs: list[str] | None = None,
) -> DbQuery[models.IssueState, Literal[False]]:
    """Build a query for issue states matching optional filters.

    Args:
        issue_state_ids: Issue state ids to filter by.
        name_longs: Exact long names to filter by.
    """
    stmt = sa.select(models.IssueState)
    if issue_state_ids:
        stmt = stmt.where(models.IssueState.issue_state_id.in_(issue_state_ids))
    if name_longs:
        stmt = stmt.where(models.IssueState.name_long.in_(name_longs))
    return DbQuery(query=stmt)
