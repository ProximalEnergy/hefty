from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_event_loss_types(  # nosemgrep: python-enforce-keyword-only-args
    *,
    db: AsyncSession,
):
    """todo

    Args:
        db: TODO: describe.
    """
    query = select(models.EventLossType)
    result = await db.execute(query)
    return result.scalars().all()
