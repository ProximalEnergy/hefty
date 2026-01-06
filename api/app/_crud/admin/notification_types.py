from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_notification_types(
    *,
    db: AsyncSession,
) -> list[models.NotificationType]:
    """Get all notification types.

    Args:
        db: Database session.
    """
    query = select(models.NotificationType)
    result = await db.execute(query)
    return list(result.scalars().all())
