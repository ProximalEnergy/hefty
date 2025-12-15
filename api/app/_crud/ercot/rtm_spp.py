import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_ercot_rtm_spp(
    db: AsyncSession,
    *,
    settlement_point_ids: list[int] = [],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """todo

    Args:
        db: TODO: describe.
        settlement_point_ids: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    query = select(models.RTMSPP)

    if settlement_point_ids:
        query = query.where(
            models.RTMSPP.settlement_point_id.in_(settlement_point_ids),
        )
    if start:
        query = query.where(models.RTMSPP.time >= start)
    if end:
        query = query.where(models.RTMSPP.time < end)

    result = await db.execute(query)
    return result.scalars().all()
