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
    query = (
        select(models.SCEDLoad)
        .where(models.SCEDLoad.resource_id == resource_id)
        .where(models.SCEDLoad.time >= start)
        .where(models.SCEDLoad.time < end)
    )
    result = await db.execute(query)
    return result.scalars().all()
