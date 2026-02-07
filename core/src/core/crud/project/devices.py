from typing import Any, Literal

from sqlalchemy import exists, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, noload

from core import models
from core.db_query import DbQuery
from core.enumerations import SensorType


def get_project_device_options(*, deep: bool, include_name_long: bool = False) -> Any:
    """Return loader options for device queries.

    Args:
        deep: Whether to eager-load related device type data.
        include_name_long: Load device type name_long only when True.
    """
    if deep:
        options = joinedload(models.Device.device_type)
    elif include_name_long:
        options = joinedload(models.Device.device_type).load_only(
            models.DeviceType.device_type_id,
            models.DeviceType.name_long,
        )
    else:
        options = noload(models.Device.device_type)

    return options


def get_project_devices(
    *,
    device_ids: list[int] = [],
    device_type_ids: list[int] = [],
    parent_device_ids: list[int | None] = [],
    name_short: str = "",
    name_long: str = "",
    deep: bool = False,
    include_name_long: bool = False,
    device_id_descendent_of: int | None = None,
    device_id_path_ancestor_of: str | None = None,
    with_tags: bool = False,
) -> DbQuery[models.Device, Literal[False]]:
    """
    Retrieve a list of devices from the database based on various filtering criteria.

    Args:
        device_ids (list[int], optional): A list of specific device IDs to filter by.
        device_type_ids (list[int], optional): A list of device type IDs to filter by.
        parent_device_ids (list[int], optional): A list of parent device IDs to filter
            by.
        name_short (str, optional): A short name to filter devices by.
        name_long (str, optional): A long name to filter devices by.
        deep (bool, optional): A flag indicating whether to load related data.
        include_name_long (bool, optional): A flag indicating whether to load
            device_type relationship to access device_type.name_long.
        device_id_descendent_of (Optional[int], optional): A device ID to filter devices
            that are descendants of it.

    Returns:
        list: A list of devices that match the filtering criteria.
    """
    options = get_project_device_options(deep=deep, include_name_long=include_name_long)

    stmt = select(models.Device).options(options)

    if device_ids:
        stmt = stmt.where(models.Device.device_id.in_(device_ids))
    if device_type_ids:
        stmt = stmt.where(models.Device.device_type_id.in_(device_type_ids))
    if parent_device_ids:
        stmt = stmt.where(models.Device.parent_device_id.in_(parent_device_ids))
    if name_short:
        stmt = stmt.where(models.Device.name_short == name_short)
    if name_long:
        stmt = stmt.where(models.Device.name_long == name_long)
    if with_tags:
        tag_exists = (
            exists()
            .where(models.Tag.device_id == models.Device.device_id)
            .where(models.Tag.sensor_type_id != SensorType.GHOST_UNKNOWN)
        )
        stmt = stmt.where(tag_exists)
    if device_id_descendent_of is not None:
        stmt = stmt.where(text(f"device_id_path ~ '*.{device_id_descendent_of}.*'"))
    if device_id_path_ancestor_of is not None:
        stmt = stmt.where(
            text(
                f"'{device_id_path_ancestor_of}'::ltree <@ device_id_path "
                f"and device_id_path <> '{device_id_path_ancestor_of}'::ltree",
            ),
        )

    return DbQuery(query=stmt)


def get_project_device(
    *,
    device_id: int,
    deep: bool,
    include_name_long: bool = False,
) -> DbQuery[models.Device, Literal[True]]:
    """Fetch a single device by id with optional related data.

    Args:
        device_id: Device id to fetch.
        deep: Whether to eager-load related device type data.
        include_name_long: Load device type name_long only when True.
    """
    options = get_project_device_options(deep=deep, include_name_long=include_name_long)
    stmt = (
        select(models.Device)
        .options(options)
        .where(models.Device.device_id == device_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


# --- ASYNC SECTION ---
async def get_project_devices_async(
    db: AsyncSession,
    *,
    device_ids: list[int] = [],
    device_type_ids: list[int] = [],
    parent_device_ids: list[int | None] = [],
    name_short: str = "",
    name_long: str = "",
    deep: bool = False,
    include_name_long: bool = False,
    device_id_descendent_of: int | None = None,
    device_id_path_ancestor_of: str | None = None,
    with_tags: bool = False,
) -> list[models.Device]:
    """
    Retrieve a list of devices from the database based on various filtering criteria.

    Args:
        device_ids (list[int], optional): A list of specific device IDs to filter by.
        device_type_ids (list[int], optional): A list of device type IDs to filter by.
        parent_device_ids (list[int], optional): A list of parent device IDs to filter
            by.
        name_short (str, optional): A short name to filter devices by.
        name_long (str, optional): A long name to filter devices by.
        deep (bool, optional): A flag indicating whether to load related data.
        include_name_long (bool, optional): A flag indicating whether to load
            device_type relationship to access device_type.name_long.
        device_id_descendent_of (Optional[int], optional): A device ID to filter devices
            that are descendants of it.

    Returns:
        list: A list of devices that match the filtering criteria.
    """
    options = get_project_device_options(deep=deep, include_name_long=include_name_long)

    stmt = select(models.Device).options(options)

    if device_ids:
        stmt = stmt.where(models.Device.device_id.in_(device_ids))
    if device_type_ids:
        stmt = stmt.where(models.Device.device_type_id.in_(device_type_ids))
    if parent_device_ids:
        stmt = stmt.where(models.Device.parent_device_id.in_(parent_device_ids))
    if name_short:
        stmt = stmt.where(models.Device.name_short == name_short)
    if name_long:
        stmt = stmt.where(models.Device.name_long == name_long)
    if with_tags:
        tag_exists = (
            exists()
            .where(models.Tag.device_id == models.Device.device_id)
            .where(models.Tag.sensor_type_id != SensorType.GHOST_UNKNOWN)
        )
        stmt = stmt.where(tag_exists)
    if device_id_descendent_of is not None:
        stmt = stmt.where(text(f"device_id_path ~ '*.{device_id_descendent_of}.*'"))
    if device_id_path_ancestor_of is not None:
        stmt = stmt.where(
            text(
                f"'{device_id_path_ancestor_of}'::ltree <@ device_id_path "
                f"and device_id_path <> '{device_id_path_ancestor_of}'::ltree",
            ),
        )

    result = await db.execute(stmt)
    return list(result.scalars().all())
