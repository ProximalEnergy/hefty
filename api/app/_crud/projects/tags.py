import re

from sqlalchemy import func
from sqlalchemy.orm import Session

from core import models


def _convert_pattern_to_regex(*, pattern: str) -> str:
    """
    Convert pattern to regex: replace [INT] with ([0-9]+) and escape the rest.
    Preserves digit groups while escaping special regex characters.
    """
    # Convert pattern to regex: replace [INT] with ([0-9]+) and escape the rest
    regex = pattern.replace("[INT]", "([0-9]+)")

    # Escape special regex characters but preserve the digit groups we just added
    temp_placeholder = "___DIGIT_GROUP___"
    regex = regex.replace("([0-9]+)", temp_placeholder)
    regex = re.escape(regex)
    regex = regex.replace(temp_placeholder, "([0-9]+)")

    # Anchor to full string to avoid substring overmatches
    return f"^{regex}$"


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
    Also returns one example tag_id for each group.
    """
    query = project_db.query(
        models.Tag.sensor_type_id,
        models.Tag.name_scada,
        models.Tag.scada_type,
        models.Tag.unit_scada,
        models.Tag.unit_offset,
        models.Tag.unit_scale,
        func.count(models.Tag.tag_id).label("count"),
        func.min(models.Tag.tag_id).label("example_tag_id"),
    )

    # Apply base filters
    query = query.filter(models.Tag.device_id != 0)
    query = query.filter(models.Tag.name_scada is not None)  # type: ignore[arg-type]

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


def get_tags_by_pattern_digits_only(project_db: Session, *, pattern: str):
    """
    Get all tags that match a given pattern where [INT] matches digits only.
    Uses Postgres regex (~) and escapes literal pieces.
    Filters out ghost tags and null names.
    """
    regex = _convert_pattern_to_regex(pattern=pattern)

    return (
        project_db.query(models.Tag)
        .filter(models.Tag.device_id != 0)
        .filter(models.Tag.name_scada.op("~")(regex))
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


def update_tags_sensor_type_by_pattern_bulk(
    project_db: Session,
    *,
    pattern: str,
    sensor_type_id: int,
    unit_scale: float | None = None,
    unit_offset: float | None = None,
):
    """
    Bulk update sensor_type_id and optionally unit_scale/unit_offset for tags matching a pattern.
    Uses SQLAlchemy bulk update for better performance with large tag sets.
    """
    regex = _convert_pattern_to_regex(pattern=pattern)

    # Execute bulk update using SQLAlchemy ORM bulk operations
    query = (
        project_db.query(models.Tag)
        .filter(models.Tag.device_id != 0)
        .filter(models.Tag.name_scada.op("~")(regex))
    )

    # Use **kwargs to avoid type inference issues
    if unit_scale is not None and unit_offset is not None:
        result = query.update(
            {
                "sensor_type_id": sensor_type_id,
                "unit_scale": unit_scale,
                "unit_offset": unit_offset,
            },
            synchronize_session=False,
        )
    elif unit_scale is not None:
        result = query.update(
            {"sensor_type_id": sensor_type_id, "unit_scale": unit_scale},
            synchronize_session=False,
        )
    elif unit_offset is not None:
        result = query.update(
            {"sensor_type_id": sensor_type_id, "unit_offset": unit_offset},
            synchronize_session=False,
        )
    else:
        result = query.update(
            {"sensor_type_id": sensor_type_id}, synchronize_session=False
        )

    project_db.commit()
    return result


def get_tag_by_id(project_db: Session, *, tag_id: int):
    """
    Get a tag by its ID.
    """
    return project_db.query(models.Tag).filter(models.Tag.tag_id == tag_id).first()


def get_sample_tags_by_pattern_digits_only(
    project_db: Session,
    *,
    pattern: str,
    limit: int = 5,
):
    """
    Get sample tags that match a given pattern where [INT] matches digits only.
    Uses Postgres regex (~) and escapes literal pieces.
    """
    regex = _convert_pattern_to_regex(pattern=pattern)

    return (
        project_db.query(models.Tag)
        .filter(models.Tag.device_id != 0)
        .filter(models.Tag.name_scada.isnot(None))
        .filter(models.Tag.name_scada.op("~")(regex))
        .order_by(models.Tag.tag_id)
        .limit(limit)
        .all()
    )
