from typing import Literal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from core import models
from core.db_query import DbQuery


def get_device_type(
    *,
    device_type_id: int,
) -> DbQuery[models.DeviceType, Literal[True]]:
    """Fetch a single device type by id.

    Args:
        device_type_id: Device type id to fetch.
    """
    stmt = (
        sa.select(models.DeviceType)
        .where(models.DeviceType.device_type_id == device_type_id)
        .limit(1)
    )
    return DbQuery(query=stmt, is_scalar=True)


async def get_device_types(
    *,
    db: AsyncSession,
    device_type_ids: list[int] = [],
    name_short: str = "",
    name_long: str = "",
):
    """
    Retrieve a list of device types from the database based on the provided filters.

    Args:
        db (AsyncSession): The database session to use for the query.
        device_type_ids (list[int], optional): A list of device type IDs to filter the
             results. Defaults to an empty list.
        name_short (str, optional): A short name to filter the device types.
             Defaults to an empty string.
        name_long (str, optional): A long name to filter the device types.
             Defaults to an empty string.

    Returns:
        list[models.DeviceType]: A list of device types matching the specified criteria.
    """
    stmt = sa.select(models.DeviceType)

    if device_type_ids:
        stmt = stmt.where(models.DeviceType.device_type_id.in_(device_type_ids))
    if name_short:
        stmt = stmt.where(models.DeviceType.name_short == name_short)
    if name_long:
        stmt = stmt.where(models.DeviceType.name_long == name_long)

    result = await db.execute(stmt)
    return result.scalars().all()
