import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_ercot_sced_load(
    db: AsyncSession,
    *,
    resource_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
):
    """Fetch SCED load records for a resource within a time range.

    Args:
        db: Async database session for the operational schema.
        resource_id: ERCOT resource ID to filter by.
        start: Inclusive start timestamp for the query window.
        end: Exclusive end timestamp for the query window.
    """
    query = (
        select(models.SCEDLoad)
        .where(models.SCEDLoad.resource_id == resource_id)
        .where(models.SCEDLoad.time >= start)
        .where(models.SCEDLoad.time < end)
    )
    result = await db.execute(query)
    return result.scalars().all()
