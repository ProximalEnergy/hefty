from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_ercot_settlement_point_types(*, db: AsyncSession, name_long: str = ""):
    query = select(models.SettlementPointType)

    if name_long:
        query = query.where(models.SettlementPointType.name_long == name_long)

    result = await db.execute(query)
    return result.scalars().all()
