from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_ercot_settlement_point_markets(*, db: AsyncSession):
    """Return all ERCOT settlement point markets.

    Args:
        db: Async SQLAlchemy session used for the query.
    """
    query = select(models.SettlementPointMarket)
    result = await db.execute(query)
    return result.scalars().all()
