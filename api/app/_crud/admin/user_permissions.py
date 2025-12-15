from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def create_user_permission(
    *,
    db: AsyncSession,
    user_permission: models.UserPermission,
):
    """Create a new user_permissions record

    Args:
        db: TODO: describe.
        user_permission: TODO: describe.
    """
    db.add(user_permission)
    await db.commit()
    await db.refresh(user_permission)
    return user_permission


async def delete_user_permission(
    db: AsyncSession,
    *,
    user_permission: models.UserPermission,
):
    """Delete a user_permissions record

    Args:
        db: TODO: describe.
        user_permission: TODO: describe.
    """
    delete_stmt = delete(models.UserPermission).where(
        models.UserPermission.user_id == user_permission.user_id,
        models.UserPermission.permission_id == user_permission.permission_id,
        models.UserPermission.project_id == user_permission.project_id,
    )
    await db.execute(delete_stmt)
    await db.commit()


async def get_user_permissions(
    db: AsyncSession,
    *,
    user_ids: list[str] | None = None,
    project_ids: list[UUID] | None = None,
) -> list[models.UserPermission]:
    """Query the user_permissions table

    Args:
        db: TODO: describe.
        user_ids: TODO: describe.
        project_ids: TODO: describe.
    """
    query = select(models.UserPermission)

    if user_ids:
        query = query.where(models.UserPermission.user_id.in_(user_ids))
    if project_ids:
        query = query.where(models.UserPermission.project_id.in_(project_ids))

    result = await db.execute(query)
    return list(result.scalars().all())
