from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_ercot_dmes(*, db: AsyncSession):
    """Return all ERCOT DME records.

    Args:
        db: Async SQLAlchemy session used for the query.
    """
    query = select(models.DME)
    result = await db.execute(query)
    return result.scalars().all()
