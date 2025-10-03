from sqlalchemy.orm import Session

from app import interfaces
from core import models


def get_sensor_type(*, db: Session, sensor_type_id: int):
    return (
        db.query(models.SensorType)
        .filter(models.SensorType.sensor_type_id == sensor_type_id)
        .first()
    )


def get_sensor_types(
    db: Session,
    *,
    sensor_type_ids: list[int] | None = [],
    name_short: str = "",
    name_long: str = "",
    name_metric: str = "",
    unit: str = "",
):
    query = db.query(models.SensorType)

    if sensor_type_ids:
        query = query.filter(models.SensorType.sensor_type_id.in_(sensor_type_ids))
    if name_short:
        query = query.filter(models.SensorType.name_short == name_short)
    if name_long:
        query = query.filter(models.SensorType.name_long == name_long)
    if name_metric:
        query = query.filter(models.SensorType.name_metric == name_metric)
    if unit:
        query = query.filter(models.SensorType.unit == unit)

    return query.all()


def create_sensor_type(*, db: Session, sensor_type: interfaces.SensorType):
    db_sensor_type = models.SensorType(
        sensor_type_id=sensor_type.sensor_type_id,
        device_type_id=sensor_type.device_type_id,
        name_short=sensor_type.name_short,
        name_long=sensor_type.name_long,
        name_metric=sensor_type.name_metric,
        unit=sensor_type.unit,
        description=sensor_type.description,
    )
    db.add(db_sensor_type)
    db.commit()
    db.refresh(db_sensor_type)
    return db_sensor_type


def update_sensor_type(
    *, db: Session, sensor_type_id: int, sensor_type: interfaces.SensorType
):
    db_sensor_type = (
        db.query(models.SensorType)
        .filter(models.SensorType.sensor_type_id == sensor_type_id)
        .first()
    )

    if not db_sensor_type:
        return None

    db_sensor_type.device_type_id = sensor_type.device_type_id
    db_sensor_type.name_short = sensor_type.name_short
    db_sensor_type.name_long = sensor_type.name_long
    db_sensor_type.name_metric = sensor_type.name_metric
    db_sensor_type.unit = sensor_type.unit
    db_sensor_type.description = sensor_type.description

    db.commit()
    db.refresh(db_sensor_type)
    return db_sensor_type


def get_next_sensor_type_id(*, db: Session) -> int:
    """Get the next available sensor_type_id"""
    max_id = (
        db.query(models.SensorType.sensor_type_id)
        .order_by(models.SensorType.sensor_type_id.desc())
        .first()
    )
    return (max_id[0] if max_id else 0) + 1
