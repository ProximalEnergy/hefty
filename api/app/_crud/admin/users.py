import secrets

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces import UserInterface
from core import models


async def create_user(
    *,
    db: AsyncSession,
    user: UserInterface,
):
    """Create a user record.

    Args:
        db: Database session.
        user: User payload to persist.
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
    """Delete a user and any related records.

    Args:
        db: Database session.
        user_id: Identifier of the user to delete.
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
    """Generate a new API key for a user.

    Args:
        db: Database session.
        user_id: Identifier of the user to update.
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
    """Remove a user's API key.

    Args:
        db: Database session.
        user_id: Identifier of the user to update.
    """
    stmt = (
        update(models.User).where(models.User.user_id == user_id).values(api_key=None)
    )
    await db.execute(stmt)
    await db.commit()
