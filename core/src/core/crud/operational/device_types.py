from typing import Literal

import sqlalchemy as sa
from core.db_query import DbQuery

from core import models


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


def get_device_types(
    *,
    device_type_ids: list[int] = [],
    name_short: str = "",
    name_long: str = "",
) -> DbQuery[models.DeviceType, Literal[False]]:
    """Retrieve device types from the database based on provided filters.

    Args:
        device_type_ids: Device type IDs to filter results.
        name_short: Short name to filter device types.
        name_long: Long name to filter device types.
    """
    stmt = sa.select(models.DeviceType)

    if device_type_ids:
        stmt = stmt.where(models.DeviceType.device_type_id.in_(device_type_ids))
    if name_short:
        stmt = stmt.where(models.DeviceType.name_short == name_short)
    if name_long:
        stmt = stmt.where(models.DeviceType.name_long == name_long)

    return DbQuery(query=stmt)
