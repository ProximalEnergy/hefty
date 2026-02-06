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
    """Fetch RTM settlement point prices with optional filters.

    Args:
        db: Async SQLAlchemy session used for the query.
        settlement_point_ids: Settlement point IDs to filter by.
        start: Inclusive start timestamp for filtering.
        end: Exclusive end timestamp for filtering.
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
