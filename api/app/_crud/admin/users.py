import secrets
import uuid

import sqlalchemy as sa
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces import User
from core import models


async def get_user(*, db: AsyncSession, user_id):
    """todo

    Args:
        db: TODO: describe.
        user_id: TODO: describe.
    """
    query = select(models.User).where(models.User.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_users(
    *,
    db: AsyncSession,
    company_ids: list[uuid.UUID] | None = None,
    user_ids: list[str] | None = None,
):
    """todo

    Args:
        db: TODO: describe.
        company_ids: TODO: describe.
        user_ids: TODO: describe.
    """
    query = (
        select(
            models.User,
            sa.func.array_agg(models.UserProject.operational_project_id).label(
                "project_ids",
            ),
        )
        .outerjoin(
            models.UserProject,
            models.User.user_id == models.UserProject.user_id,
        )
        .group_by(models.User.user_id)
    )

    if company_ids:
        query = query.where(models.User.company_id.in_(company_ids))

    if user_ids:
        query = query.where(models.User.user_id.in_(user_ids))

    result = await db.execute(query)
    return result.all()


async def create_user(
    *,
    db: AsyncSession,
    user: User,
):
    """todo

    Args:
        db: TODO: describe.
        user: TODO: describe.
    """
    db_user = models.User(**user.model_dump())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def delete_user(
    *,
    db: AsyncSession,
    user_id: str,
):
    # Delete related records first
    # NOTE: This could be rewritten later to use a CASCADE
    # instead of deleting each record.
    """todo

    Args:
        db: TODO: describe.
        user_id: TODO: describe.
    """
    await db.execute(
        delete(models.UserProject).where(models.UserProject.user_id == user_id)
    )
    await db.execute(
        delete(models.UserPermission).where(models.UserPermission.user_id == user_id)
    )
    await db.execute(
        delete(models.UserSubscription).where(
            models.UserSubscription.user_id == user_id
        )
    )
    await db.execute(delete(models.Feedback).where(models.Feedback.user_id == user_id))

    # Delete the user
    await db.execute(delete(models.User).where(models.User.user_id == user_id))
    await db.commit()


async def create_api_key(
    db: AsyncSession,
    *,
    user_id: str,
):
    """todo

    Args:
        db: TODO: describe.
        user_id: TODO: describe.
    """
    stmt = (
        update(models.User)
        .where(models.User.user_id == user_id)
        .values(api_key=secrets.token_urlsafe(32))
    )
    await db.execute(stmt)
    await db.commit()


async def delete_api_key(
    db: AsyncSession,
    *,
    user_id: str,
):
    """todo

    Args:
        db: TODO: describe.
        user_id: TODO: describe.
    """
    stmt = (
        update(models.User).where(models.User.user_id == user_id).values(api_key=None)
    )
    await db.execute(stmt)
    await db.commit()
