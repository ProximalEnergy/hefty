from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_permissions(
    db: AsyncSession,
    *,
    permission_ids: list[int] | None = None,
) -> list[models.Permission]:
    """Query the permissions table"""
    query = select(models.Permission)
    # Cannot be `if permission_ids` because permission_ids can be an empty list
    # which is falsy
    if permission_ids is not None:
        query = query.where(models.Permission.permission_id.in_(permission_ids))
    result = await db.execute(query)
    return list(result.scalars().all())
