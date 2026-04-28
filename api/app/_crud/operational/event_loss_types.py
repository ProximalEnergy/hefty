from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_event_loss_types(  # no-star-syntax
    *,
    db: AsyncSession,
):
    """todo

    Args:
        db: Description for db.
    """
    query = select(models.EventLossType)
    result = await db.execute(query)
    return result.scalars().all()
