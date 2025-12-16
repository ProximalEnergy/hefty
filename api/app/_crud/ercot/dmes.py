from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_ercot_dmes(*, db: AsyncSession):
    """todo

    Args:
        db: TODO: describe.
    """
    query = select(models.DME)
    result = await db.execute(query)
    return result.scalars().all()
