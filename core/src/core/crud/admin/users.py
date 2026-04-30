import uuid
from typing import Any, Literal

from sqlalchemy import select

from core import models
from core.db_query import DbQuery


def get_user_by_id(*, user_id: str) -> DbQuery[models.User, Literal[True]]:
    """Get a user by ID.

    Args:
        user_id: User ID.

    Returns:
        DbQuery for User model.
    """
    query = select(models.User).where(models.User.user_id == user_id)
    return DbQuery(query=query, is_scalar=True)


def get_users(
    *,
    company_ids: list[uuid.UUID] | None = None,
    user_ids: list[str] | None = None,
) -> DbQuery[Any, Literal[False]]:
    """Get users by company IDs or user IDs.

    Args:
        company_ids: List of company IDs.
        user_ids: List of user IDs.

    Returns:
        DbQuery for users and their project IDs.
    """
    query = select(
        models.User,
        models.UserProject.operational_project_id.label("project_ids"),
    ).outerjoin(
        models.UserProject,
        models.User.user_id == models.UserProject.user_id,
    )

    if company_ids:
        query = query.where(models.User.company_id.in_(company_ids))

    if user_ids:
        query = query.where(models.User.user_id.in_(user_ids))

    return DbQuery(query=query)
