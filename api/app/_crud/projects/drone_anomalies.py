import uuid
from collections.abc import Sequence

from core.models import DroneAnomaly
from sqlalchemy.orm import Session

from app.interfaces import DroneAnomalyCreate


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


def update_anomalies_with_event_id(
    *,
    db: Session,
    anomaly_uuids: list[uuid.UUID],
    event_id: int,
):
    """
    Update drone anomalies with the event_id they are associated with.
    Note: This function does NOT commit the transaction - it should be called within an existing transaction.
    """
    import logging

    logging.info(
        f"🔧 update_anomalies_with_event_id called: event_id={event_id}, anomaly_uuids={anomaly_uuids}"
    )

    # First, check how many anomalies exist with these UUIDs
    existing_count = (
        db.query(DroneAnomaly)
        .filter(DroneAnomaly.anomaly_uuid.in_(anomaly_uuids))
        .count()
    )

    logging.info(
        f"📊 Found {existing_count} existing anomalies out of {len(anomaly_uuids)} requested UUIDs"
    )

    # Update the anomalies using a more efficient bulk update
    from sqlalchemy import update

    stmt = (
        update(DroneAnomaly)
        .where(DroneAnomaly.anomaly_uuid.in_(anomaly_uuids))
        .values(event_id=event_id)
    )

    result = db.execute(stmt)

    logging.info(
        f"🔄 Updated {result.rowcount} anomalies with event_id {event_id}"  # type: ignore[attr-defined]
    )

    # Note: No commit here - let the calling function handle the transaction


def bulk_update_anomalies_with_event_ids(
    *,
    db: Session,
    event_mapping: dict[int, list[uuid.UUID]],
):
    """
    Bulk update anomalies with event_ids using a single SQL operation.
    This is much faster than individual updates.

    Args:
        db: Database session
        event_mapping: Dict mapping event_id -> list of anomaly UUIDs
    """
    from sqlalchemy import case, update

    if not event_mapping:
        return

    # Flatten into a single list of all UUIDs
    all_uuids = [u for uuids in event_mapping.values() for u in uuids]

    # Create a CASE statement to map each UUID to its corresponding event_id
    case_stmt = case(
        *(
            (DroneAnomaly.anomaly_uuid == u, e_id)
            for e_id, uuids in event_mapping.items()
            for u in uuids
        ),
        else_=DroneAnomaly.event_id,  # Keep existing value if no match
    )

    # Execute the bulk update
    stmt = (
        update(DroneAnomaly)
        .where(DroneAnomaly.anomaly_uuid.in_(all_uuids))
        .values(event_id=case_stmt)
    )

    db.execute(stmt)

    # Note: No commit here - let the calling function handle the transaction


def get_anomalies_by_event_id(*, db: Session, event_id: int) -> Sequence[DroneAnomaly]:
    """
    Get all anomalies for a given event from the project-specific schema.
    """
    return db.query(DroneAnomaly).filter(DroneAnomaly.event_id == event_id).all()
