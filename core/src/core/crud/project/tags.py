from collections.abc import Sequence
from typing import Any, Literal

from core.db_query import DbQuery
from core.enumerations import SensorTypeEnum
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, joinedload, noload

from core import models


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


def _label_columns(*, model: Any, prefix: str) -> list[Any]:
    """Helper to label all columns of a model with a prefix.

    Args:
        model: SQLAlchemy mapped model whose columns will be labeled.
        prefix: String prepended to each column name (e.g. "device").
    """
    return [
        getattr(model, column.name).label(f"{prefix}_{column.name}")
        for column in model.__table__.columns
    ]


def _get_project_tag_options_v2(*, deep: bool) -> list[Any]:
    """Return labeled columns for tag queries.

    Args:
        deep: When True, also include labeled columns for Device,
            DeviceType, SensorType, and DataType.
    """
    columns = [
        getattr(models.Tag, column.name).label(column.name)
        for column in models.Tag.__table__.columns
    ]
    if deep:
        columns.extend(
            [
                *_label_columns(model=models.Device, prefix="device"),
                *_label_columns(model=models.DeviceType, prefix="device_type"),
                *_label_columns(model=models.SensorType, prefix="sensor_type"),
                *_label_columns(model=models.DataType, prefix="data_type"),
            ]
        )
    return columns


def get_project_tags_v2(
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
) -> DbQuery[
    Any,
    Literal[False],
]:
    """Query tags with a variety of filter options.

    Args:
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
    """
    columns = _get_project_tag_options_v2(deep=deep)
    stmt = select(*columns)

    if deep:
        stmt = (
            stmt.outerjoin(
                models.Device, models.Tag.device_id == models.Device.device_id
            )
            .outerjoin(
                models.DeviceType,
                models.Device.device_type_id == models.DeviceType.device_type_id,
            )
            .outerjoin(
                models.SensorType,
                models.Tag.sensor_type_id == models.SensorType.sensor_type_id,
            )
            .outerjoin(
                models.DataType,
                models.Tag.data_type_id == models.DataType.data_type_id,
            )
        )

    if tag_ids:
        stmt = stmt.where(models.Tag.tag_id.in_(tag_ids))
    if in_tsdb is not None:
        stmt = stmt.where(models.Tag.in_tsdb == in_tsdb)
    if device_ids:
        stmt = stmt.where(models.Tag.device_id.in_(device_ids))
    if sensor_type_ids:
        stmt = stmt.where(models.Tag.sensor_type_id.in_(sensor_type_ids))
    if sensor_type_name_shorts:
        if deep:
            stmt = stmt.where(models.SensorType.name_short.in_(sensor_type_name_shorts))
        else:
            stmt = stmt.where(
                models.Tag.sensor_type.has(
                    models.SensorType.name_short.in_(sensor_type_name_shorts),
                ),
            )
    if data_type_ids:
        stmt = stmt.where(models.Tag.data_type_id.in_(data_type_ids))
    if name_short:
        stmt = stmt.where(models.Tag.name_short == name_short)
    if name_long:
        stmt = stmt.where(models.Tag.name_long == name_long)
    if name_scada:
        stmt = stmt.where(models.Tag.name_scada == name_scada)
    if has_sensor_type_id:
        stmt = stmt.where(models.Tag.sensor_type_id != None)  # noqa: E711
    if device_type_ids:
        if deep:
            stmt = stmt.where(models.Device.device_type_id.in_(device_type_ids))
        else:
            stmt = stmt.where(
                models.Tag.device.has(models.Device.device_type_id.in_(device_type_ids))
            )
    if not include_ghost_tags:
        stmt = stmt.where(models.Tag.device_id != 0)
        stmt = stmt.where(models.Tag.sensor_type_id != SensorTypeEnum.GHOST_UNKNOWN)
    return DbQuery(query=stmt, is_scalar=False)


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
