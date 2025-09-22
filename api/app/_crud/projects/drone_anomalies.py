import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.interfaces import DroneAnomalyCreate
from core.models import DroneAnomaly


def bulk_create_drone_anomalies(
    *,
    db: Session,
    anomalies_data: list[DroneAnomalyCreate],
    inspection_uuid: uuid.UUID,
):
    """
    Delete all existing anomalies for an inspection and bulk insert new ones.
    """
    # Delete existing anomalies for this inspection to ensure a clean sync
    db.query(DroneAnomaly).filter(
        DroneAnomaly.inspection_uuid == inspection_uuid
    ).delete(synchronize_session=False)

    db_anomalies = [DroneAnomaly(**data.model_dump()) for data in anomalies_data]
    db.add_all(db_anomalies)
    db.commit()


def get_anomalies_by_inspection_uuid(
    *, db: Session, inspection_uuid: uuid.UUID
) -> Sequence[DroneAnomaly]:
    """
    Get all anomalies for a given inspection from the project-specific schema.
    """
    return (
        db.query(DroneAnomaly)
        .filter(DroneAnomaly.inspection_uuid == inspection_uuid)
        .all()
    )


def get_anomaly_count_by_inspection_uuid(
    *, db: Session, inspection_uuid: uuid.UUID
) -> int:
    """
    Get the count of anomalies for a given inspection from the project-specific schema.
    """
    return (
        db.query(DroneAnomaly)
        .filter(DroneAnomaly.inspection_uuid == inspection_uuid)
        .count()
    )


def bulk_create_drone_anomalies_incremental(
    *,
    db: Session,
    anomalies_data: list[DroneAnomalyCreate],
    inspection_uuid: uuid.UUID,
):
    """
    Bulk insert new anomalies without deleting existing ones.
    """
    db_anomalies = [DroneAnomaly(**data.model_dump()) for data in anomalies_data]
    db.add_all(db_anomalies)
    db.commit()
