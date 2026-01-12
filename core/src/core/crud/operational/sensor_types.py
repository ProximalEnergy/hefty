from typing import Literal

from sqlalchemy import select

from core import models
from core.db_query import DbQuery


def get_sensor_type(
    *, sensor_type_id: int
) -> DbQuery[models.SensorType, Literal[True]]:
    """TODO: add description.

    Args:
        sensor_type_id: TODO: describe.
    """
    stmt = select(models.SensorType).where(
        models.SensorType.sensor_type_id == sensor_type_id
    )
    return DbQuery(query=stmt, is_scalar=True)


def get_sensor_types(
    *,
    sensor_type_ids: list[int] | None = None,
    name_short: str | None = None,
    name_long: str | None = None,
    name_metric: str | None = None,
    unit: str | None = None,
) -> DbQuery[models.SensorType, Literal[False]]:
    """TODO: add description.

    Args:
        sensor_type_ids: TODO: describe.
        name_short: TODO: describe.
        name_long: TODO: describe.
        name_metric: TODO: describe.
        unit: TODO: describe.
    """
    stmt = select(models.SensorType)

    if sensor_type_ids:
        stmt = stmt.where(models.SensorType.sensor_type_id.in_(sensor_type_ids))
    if name_short:
        stmt = stmt.where(models.SensorType.name_short == name_short)
    if name_long:
        stmt = stmt.where(models.SensorType.name_long == name_long)
    if name_metric:
        stmt = stmt.where(models.SensorType.name_metric == name_metric)
    if unit:
        stmt = stmt.where(models.SensorType.unit == unit)

    return DbQuery(query=stmt)
