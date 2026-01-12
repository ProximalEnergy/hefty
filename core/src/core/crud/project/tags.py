from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, joinedload, noload

from core import models
from core.enumerations import SensorType
from core.model_list import ModelItem, ModelList


def _get_project_tag_options(*, deep: bool) -> Any:
    """Return loader options for tag queries.

    Args:
        deep: Whether to eager-load tag relationships.
    """
    if deep:
        options = (
            joinedload(models.Tag.device),
            joinedload(models.Tag.sensor_type),
            joinedload(models.Tag.data_type),
        )
    else:
        options = (
            noload(models.Tag.device),
            noload(models.Tag.sensor_type),
            noload(models.Tag.data_type),
        )

    return options


def get_project_tag(
    db: Session, tag_id: int, *, deep: bool, return_query: bool = False
) -> ModelItem[models.Tag]:
    """Fetch a single tag by id.

    Args:
        db: Project database session.
        tag_id: Tag id to fetch.
        deep: Whether to eager-load tag relationships.
        return_query: Return the query without executing when True.
    """
    options = _get_project_tag_options(deep=deep)
    query = db.query(models.Tag).options(*options).where(models.Tag.tag_id == tag_id)
    return ModelItem(query=query, return_query=return_query)


def get_project_tags(
    db: Session,
    *,
    tag_ids: list[int] = [],
    in_tsdb: bool | None = None,
    device_ids: list[int] = [],
    device_type_ids: list[int] = [],
    sensor_type_ids: Sequence[int] = [],
    sensor_type_name_shorts: list[str] = [],
    data_type_ids: list[int] = [],
    name_short: str = "",
    name_long: str = "",
    name_scada: str = "",
    deep: bool = False,
    include_ghost_tags: bool = False,
    has_sensor_type_id: bool = False,
    return_query: bool = False,
) -> ModelList[models.Tag]:
    """Query tags with a variety of filter options.

    Args:
        db: Project database session.
        tag_ids: Tag ids to filter by.
        in_tsdb: Filter by presence in TSDB.
        device_ids: Device ids to filter by.
        device_type_ids: Device type ids to filter by.
        sensor_type_ids: Sensor type ids to filter by.
        sensor_type_name_shorts: Sensor type short names to filter by.
        data_type_ids: Data type ids to filter by.
        name_short: Tag name_short to filter by.
        name_long: Tag name_long to filter by.
        name_scada: Tag name_scada to filter by.
        deep: Whether to eager-load tag relationships.
        include_ghost_tags: Include ghost tags when True.
        has_sensor_type_id: Require a non-null sensor_type_id when True.
        return_query: Return the query without executing when True.
    """
    options = _get_project_tag_options(deep=deep)

    query = db.query(models.Tag).options(*options)

    if tag_ids:
        query = query.where(models.Tag.tag_id.in_(tag_ids))
    if in_tsdb is not None:
        query = query.where(models.Tag.in_tsdb == in_tsdb)
    if device_ids:
        query = query.where(models.Tag.device_id.in_(device_ids))
    if sensor_type_ids:
        query = query.where(models.Tag.sensor_type_id.in_(sensor_type_ids))
    if sensor_type_name_shorts:
        query = query.where(
            models.Tag.sensor_type.has(
                models.SensorType.name_short.in_(sensor_type_name_shorts),
            ),
        )
    if data_type_ids:
        query = query.where(models.Tag.data_type_id.in_(data_type_ids))
    if name_short:
        query = query.where(models.Tag.name_short == name_short)
    if name_long:
        query = query.where(models.Tag.name_long == name_long)
    if name_scada:
        query = query.where(models.Tag.name_scada == name_scada)
    if has_sensor_type_id:
        query = query.where(models.Tag.sensor_type_id != None)  # noqa: E711
    if device_type_ids:
        query = query.where(
            models.Tag.device.has(models.Device.device_type_id.in_(device_type_ids))
        )
    if not include_ghost_tags:
        query = query.where(models.Tag.device_id != 0)
        query = query.where(models.Tag.sensor_type_id != SensorType.GHOST_UNKNOWN)
    return ModelList(query=query, return_query=return_query)


def get_unique_sensor_type_ids_from_tags(*, db: Session) -> list[int]:
    """
    Get all unique sensor type IDs that are assigned to tags in the project.
    Includes sensor type ID 0 and sorts results in ascending order.

    Args:
        db: Database session

    Returns:
        List of unique sensor type IDs sorted in ascending order
    """
    # Get all unique sensor_type_ids from tags where sensor_type_id is not null
    # Sort at database level for better performance
    stmt = (
        select(models.Tag.sensor_type_id)
        .where(models.Tag.sensor_type_id.isnot(None))
        .distinct()
        .order_by(models.Tag.sensor_type_id.asc())
    )
    result = db.execute(stmt)

    # Extract the sensor_type_id values from the result tuples.
    # They should already be sorted from the database query.
    sensor_type_ids = [
        sensor_type_id
        for sensor_type_id in result.scalars().all()
        if sensor_type_id is not None
    ]

    # Ensure sensor_type_id 0 is included and maintain ascending order
    if 0 not in sensor_type_ids:
        sensor_type_ids.insert(0, 0)

    return sensor_type_ids


async def get_tags_by_regex(
    *, db: AsyncSession, regex: str, limit: int = 200, deep: bool = False
) -> list[models.Tag]:
    """Get all tags whose name_scada matches a given regex (PostgreSQL '~*' operator).

    Args:
        db: Project database session.
        regex: Regular expression to match name_scada.
        limit: Maximum number of tags to return.
        deep: Whether to eager-load tag relationships.
    """
    options = _get_project_tag_options(deep=deep)
    stmt = (
        select(models.Tag)
        .options(*options)
        .where(models.Tag.name_scada.op("~*")(regex))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
