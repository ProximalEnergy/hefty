from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_ercot_qses(*, db: AsyncSession):
    """Return all ERCOT QSE records.

    Args:
        db: Async SQLAlchemy session used for the query.
    """
    query = select(models.QSE)
    result = await db.execute(query)
    return result.scalars().all()
