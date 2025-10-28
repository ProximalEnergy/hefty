from typing import Any

from sqlalchemy.orm import Session, noload, selectinload

from core import models
from core.model_list import ModelItem, ModelList


def _get_project_tag_options(*, deep: bool) -> Any:
    if deep:
        options = (
            selectinload(models.Tag.device),
            selectinload(models.Tag.sensor_type),
            selectinload(models.Tag.data_type),
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
    options = _get_project_tag_options(deep=deep)
    query = db.query(models.Tag).options(*options).filter(models.Tag.tag_id == tag_id)
    return ModelItem(query=query, return_query=return_query)


def get_project_tags(
    db: Session,
    *,
    tag_ids: list[int] = [],
    in_tsdb: bool | None = None,
    device_ids: list[int] = [],
    sensor_type_ids: list[int] = [],
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
    options = _get_project_tag_options(deep=deep)

    query = db.query(models.Tag).options(*options)

    if tag_ids:
        query = query.filter(models.Tag.tag_id.in_(tag_ids))
    if in_tsdb is not None:
        query = query.filter(models.Tag.in_tsdb == in_tsdb)
    if device_ids:
        query = query.filter(models.Tag.device_id.in_(device_ids))
    if sensor_type_ids:
        query = query.filter(models.Tag.sensor_type_id.in_(sensor_type_ids))
    if sensor_type_name_shorts:
        query = query.filter(
            models.Tag.sensor_type.has(
                models.SensorType.name_short.in_(sensor_type_name_shorts),
            ),
        )
    if data_type_ids:
        query = query.filter(models.Tag.data_type_id.in_(data_type_ids))
    if name_short:
        query = query.filter(models.Tag.name_short == name_short)
    if name_long:
        query = query.filter(models.Tag.name_long == name_long)
    if name_scada:
        query = query.filter(models.Tag.name_scada == name_scada)
    if has_sensor_type_id:
        query = query.filter(models.Tag.sensor_type_id != None)  # noqa: E711
    if not include_ghost_tags:
        query = query.filter(models.Tag.device_id != 0)
        query = query.filter(models.Tag.sensor_type_id != 0)
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
    unique_sensor_type_ids = (
        db.query(models.Tag.sensor_type_id)
        .filter(models.Tag.sensor_type_id.isnot(None))
        .distinct()
        .order_by(models.Tag.sensor_type_id.asc())
        .all()
    )

    # Extract the sensor_type_id values from the result tuples
    # They should already be sorted from the database query
    sensor_type_ids = [row[0] for row in unique_sensor_type_ids]

    # Ensure sensor_type_id 0 is included and maintain ascending order
    if 0 not in sensor_type_ids:
        sensor_type_ids.insert(0, 0)

    return sensor_type_ids
