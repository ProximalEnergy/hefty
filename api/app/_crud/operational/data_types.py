from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


def get_data_type(*, data_type_id: int) -> DbQuery[models.DataType, Literal[True]]:
    """todo

    Args:
        data_type_id: TODO: describe.
    """
    query = select(models.DataType).where(models.DataType.data_type_id == data_type_id)
    return DbQuery(query=query, is_scalar=True)


async def get_data_types(
    *,
    db: AsyncSession,
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
