import re
from typing import Any, Literal, cast

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from core import models
from core.db_query import DbQuery


def _convert_pattern_to_regex(*, pattern: str) -> str:
    """Convert pattern to regex: replace [INT] with ([0-9]+) and escape the rest.
        Preserves digit groups while escaping special regex characters.

    Args:
        pattern: TODO: describe.
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


def get_sensor_type_assignments(*, project_db: Session):
    """Get sensor types and their current assignments for a project.

    Args:
        project_db: TODO: describe.
    """
    sensor_types = project_db.execute(select(models.SensorType)).scalars().all()
    assignments = []

    for sensor_type in sensor_types:
        tag_count = project_db.execute(
            select(func.count())
            .select_from(models.Tag)
            .where(
                models.Tag.sensor_type_id == sensor_type.sensor_type_id,
                models.Tag.device_id != 0,
            ),
        ).scalar_one()

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


def get_tag_by_name_short(
    *,
    name_short: str,
) -> DbQuery[models.Tag, Literal[True]]:
    """Get a tag by its name_short.

    Args:
        name_short: TODO: describe.
    """
    query = select(models.Tag).where(
        models.Tag.name_short == name_short,
        models.Tag.device_id != 0,
    )
    return DbQuery(query=query, is_scalar=True)


def update_tag_sensor_type(
    *,
    project_db: Session,
    tag: models.Tag,
    sensor_type_id: int,
):
    """Update a tag's sensor_type_id.

    Args:
        project_db: TODO: describe.
        tag: TODO: describe.
        sensor_type_id: TODO: describe.
    """
    tag.sensor_type_id = sensor_type_id
    project_db.commit()
    return tag


def get_tags_by_pattern_digits_only(*, project_db: Session, pattern: str):
    """Get all tags that match a given pattern where [INT] matches digits only.
        Uses Postgres regex (~) and escapes literal pieces.

    Args:
        project_db: TODO: describe.
        pattern: TODO: describe.
    """
    regex = _convert_pattern_to_regex(pattern=pattern)

    query = select(models.Tag).where(models.Tag.name_scada.op("~")(regex))
    return project_db.execute(query).scalars().all()


def update_tags_sensor_type_by_pattern_bulk(
    *,
    project_db: Session,
    pattern: str,
    sensor_type_id: int,
    unit_scale: float | None = None,
    unit_offset: float | None = None,
    unit_scada: str | None = None,
):
    """Bulk update sensor_type_id and optionally unit_scale/unit_offset/unit_scada
    for tags matching a pattern. Uses SQLAlchemy bulk update for better
    performance with large tag sets.

    unit_scale, unit_offset, and unit_scada are always applied, including None
    to clear values.

    Args:
        project_db: TODO: describe.
        pattern: TODO: describe.
        sensor_type_id: TODO: describe.
        unit_scale: TODO: describe.
        unit_offset: TODO: describe.
        unit_scada: TODO: describe.
    """
    regex = _convert_pattern_to_regex(pattern=pattern)

    # Build update dict - always include unit fields (including None).
    update_dict: dict[str, Any] = {"sensor_type_id": sensor_type_id}

    update_dict["unit_scale"] = unit_scale
    update_dict["unit_offset"] = unit_offset
    update_dict["unit_scada"] = unit_scada

    update_query = (
        update(models.Tag)
        .where(models.Tag.name_scada.op("~")(regex))
        .values(**update_dict)
    )
    result = cast(CursorResult[Any], project_db.execute(update_query))
    rowcount = result.rowcount or 0
    project_db.commit()
    return rowcount


def get_tag_by_id(*, project_db: Session, tag_id: int):
    """Get a tag by its ID.

    Args:
        project_db: TODO: describe.
        tag_id: TODO: describe.
    """
    query = select(models.Tag).where(models.Tag.tag_id == tag_id)
    return project_db.execute(query).scalars().first()


def get_sample_tags_by_pattern_digits_only(
    *,
    project_db: Session,
    pattern: str,
    limit: int = 5,
):
    """Get sample tags that match a given pattern where [INT] matches digits only.
        Uses Postgres regex (~) and escapes literal pieces.

    Args:
        project_db: TODO: describe.
        pattern: TODO: describe.
        limit: TODO: describe.
    """
    regex = _convert_pattern_to_regex(pattern=pattern)

    query = (
        select(models.Tag)
        .where(models.Tag.name_scada.op("~")(regex))
        .order_by(models.Tag.tag_id)
        .limit(limit)
    )
    return project_db.execute(query).scalars().all()
