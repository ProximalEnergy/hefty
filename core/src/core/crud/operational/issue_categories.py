from typing import Literal

import sqlalchemy as sa
from core.db_query import DbQuery

from core import models


def get_issue_category(
    *,
    issue_category_id: int,
) -> DbQuery[models.IssueCategory, Literal[True]]:
    """Build a query for a single issue category by id.

    Args:
        issue_category_id: Issue category id to fetch.
    """
    stmt = sa.select(models.IssueCategory).where(
        models.IssueCategory.issue_category_id == issue_category_id
    )
    return DbQuery(query=stmt, is_scalar=True)


def get_issue_categories(
    *,
    issue_category_ids: list[int] | None = None,
    name_longs: list[str] | None = None,
) -> DbQuery[models.IssueCategory, Literal[False]]:
    """Build a query for issue categories matching optional filters.

    Args:
        issue_category_ids: Issue category ids to filter by.
        name_longs: Exact long names to filter by.
    """
    stmt = sa.select(models.IssueCategory)
    if issue_category_ids:
        stmt = stmt.where(
            models.IssueCategory.issue_category_id.in_(issue_category_ids)
        )
    if name_longs:
        stmt = stmt.where(models.IssueCategory.name_long.in_(name_longs))
    return DbQuery(query=stmt)
