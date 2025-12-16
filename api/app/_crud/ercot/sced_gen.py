import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_ercot_sced_gen(
    db: AsyncSession,
    *,
    resource_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
):
    """todo

    Args:
        db: TODO: describe.
        resource_id: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    query = (
        select(models.SCEDGen)
        .where(models.SCEDGen.resource_id == resource_id)
        .where(models.SCEDGen.time >= start)
        .where(models.SCEDGen.time < end)
    )
    result = await db.execute(query)
    return result.scalars().all()
