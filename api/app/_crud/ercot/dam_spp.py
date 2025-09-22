import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_ercot_dam_spp(
    db: AsyncSession,
    *,
    settlement_point_ids: list[int] = [],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    query = select(models.DAMSPP)

    if settlement_point_ids:
        query = query.where(
            models.DAMSPP.settlement_point_id.in_(settlement_point_ids),
        )
    if start:
        query = query.where(models.DAMSPP.time >= start)
    if end:
        query = query.where(models.DAMSPP.time < end)

    result = await db.execute(query)
    return result.scalars().all()
