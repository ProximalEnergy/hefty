from sqlalchemy import select
from sqlalchemy.orm import Session

from app import interfaces
from core import models


def create_sensor_type(*, db: Session, sensor_type: interfaces.SensorType):
    """Create a sensor type record.

    Args:
        db: Database session.
        sensor_type: Sensor type payload to persist.
    """
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
    """Update a sensor type record.

    Args:
        db: Database session.
        sensor_type_id: Sensor type identifier to update.
        sensor_type: Sensor type payload with updated values.
    """
    statement = select(models.SensorType).where(
        models.SensorType.sensor_type_id == sensor_type_id,
    )
    db_sensor_type = db.execute(statement).scalar_one_or_none()

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
    """Get the next available sensor_type_id

    Args:
        db: Database session.
    """
    statement = (
        select(models.SensorType.sensor_type_id)
        .order_by(models.SensorType.sensor_type_id.desc())
        .limit(1)
    )
    max_id = db.execute(statement).scalar_one_or_none()
    return (max_id or 0) + 1
