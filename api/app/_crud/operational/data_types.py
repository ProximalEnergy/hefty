from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_data_type(
    db: AsyncSession,
    *,
    data_type_id: int,
):
    """todo

    Args:
        db: TODO: describe.
        data_type_id: TODO: describe.
    """
    query = select(models.DataType).where(models.DataType.data_type_id == data_type_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_data_types(
    db: AsyncSession,
    *,
    data_type_ids: list[int] = [],
    name_short: str = "",
):
    """todo

    Args:
        db: TODO: describe.
        data_type_ids: TODO: describe.
        name_short: TODO: describe.
    """
    query = select(models.DataType)

    if data_type_ids:
        query = query.where(models.DataType.data_type_id.in_(data_type_ids))
    if name_short:
        query = query.where(models.DataType.name_short == name_short)

    result = await db.execute(query)
    return list(result.scalars().all())
