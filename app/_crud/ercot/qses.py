from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_ercot_qses(db: AsyncSession):
    query = select(models.QSE)
    result = await db.execute(query)
    return result.scalars().all()
