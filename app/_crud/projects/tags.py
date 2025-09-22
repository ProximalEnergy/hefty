from sqlalchemy import func
from sqlalchemy.orm import Session

from core import models


def get_unique_tag_types(
    project_db: Session,
    *,
    limit: int = 500,
    include_null_sensor_types: bool = False,
    only_null_sensor_types: bool = False,
):
    """
    Get unique tag types for a project using standard query patterns.
    Groups tags by sensor_type_id, name_scada, scada_type, unit_scada, unit_offset, unit_scale.
    """
    query = project_db.query(
        models.Tag.sensor_type_id,
        models.Tag.name_scada,
        models.Tag.scada_type,
        models.Tag.unit_scada,
        models.Tag.unit_offset,
        models.Tag.unit_scale,
        func.count(models.Tag.tag_id).label("count"),
    )

    # Apply base filters
    query = query.filter(models.Tag.device_id != 0)
    query = query.filter(models.Tag.name_scada != None)

    # Apply sensor type filters
    if only_null_sensor_types:
        query = query.filter(models.Tag.sensor_type_id == 0)
    elif not include_null_sensor_types:
        query = query.filter(models.Tag.sensor_type_id > 0)

    # Group by and order
    query = query.group_by(
        models.Tag.sensor_type_id,
        models.Tag.name_scada,
        models.Tag.scada_type,
        models.Tag.unit_scada,
        models.Tag.unit_offset,
        models.Tag.unit_scale,
    )
    query = query.order_by(func.count(models.Tag.tag_id).desc())
    query = query.limit(limit)

    return query.all()


def get_sensor_type_assignments(*, project_db: Session):
    """
    Get sensor types and their current assignments for a project.
    """
    sensor_types = project_db.query(models.SensorType).all()
    assignments = []

    for sensor_type in sensor_types:
        tag_count = (
            project_db.query(models.Tag)
            .filter(
                models.Tag.sensor_type_id == sensor_type.sensor_type_id,
                models.Tag.device_id != 0,
            )
            .count()
        )

        if tag_count > 0:
            assignments.append(
                {
                    "sensor_type_id": sensor_type.sensor_type_id,
                    "sensor_type_name_short": sensor_type.name_short,
                    "sensor_type_name_long": sensor_type.name_long,
                    "sensor_type_name_metric": sensor_type.name_metric,
                    "sensor_type_unit": sensor_type.unit,
                    "tag_count": tag_count,
                }
            )

    return assignments


def get_tag_by_name_short(project_db: Session, *, name_short: str):
    """
    Get a tag by its name_short.
    """
    return (
        project_db.query(models.Tag)
        .filter(models.Tag.name_short == name_short, models.Tag.device_id != 0)
        .first()
    )


def update_tag_sensor_type(
    project_db: Session,
    *,
    tag: models.Tag,
    sensor_type_id: int,
):
    """
    Update a tag's sensor_type_id.
    """
    tag.sensor_type_id = sensor_type_id
    project_db.commit()
    return tag


def get_tags_by_pattern(project_db: Session, *, pattern: str):
    """
    Get all tags that match a given pattern.
    """
    sql_pattern = pattern.replace("[INT]", "%")
    return (
        project_db.query(models.Tag)
        .filter(models.Tag.name_scada.like(sql_pattern))
        .all()
    )


def update_tags_sensor_type(
    project_db: Session,
    *,
    tags: list[models.Tag],
    sensor_type_id: int,
    unit_scale: float | None = None,
    unit_offset: float | None = None,
):
    """
    Update sensor_type_id and optionally unit_scale/unit_offset for multiple tags.
    """
    updated_count = 0
    for tag in tags:
        tag.sensor_type_id = sensor_type_id
        if unit_scale is not None:
            tag.unit_scale = unit_scale
        if unit_offset is not None:
            tag.unit_offset = unit_offset
        updated_count += 1

    project_db.commit()
    return updated_count


def get_tag_by_id(project_db: Session, *, tag_id: int):
    """
    Get a tag by its ID.
    """
    return project_db.query(models.Tag).filter(models.Tag.tag_id == tag_id).first()


def get_sample_tags_by_pattern(
    project_db: Session,
    *,
    pattern: str,
    limit: int = 5,
):
    """
    Get sample tags that match a given pattern.
    """
    sql_pattern = pattern.replace("[INT]", "%")
    return (
        project_db.query(models.Tag)
        .filter(
            models.Tag.name_scada.like(sql_pattern),
            models.Tag.name_scada.isnot(None),
        )
        .order_by(models.Tag.tag_id)
        .limit(limit)
        .all()
    )


def get_sample_tag_id_by_pattern(project_db: Session, *, pattern: str):
    """
    Get a sample tag_id for a given pattern.
    """
    sql_pattern = pattern.replace("[INT]", "%")
    tag = (
        project_db.query(models.Tag.tag_id)
        .filter(models.Tag.name_scada.like(sql_pattern))
        .first()
    )
    return tag[0] if tag else None
