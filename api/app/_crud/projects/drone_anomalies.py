import logging
import uuid
from collections.abc import Sequence

from core.models import DroneAnomaly
from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session

from app.interfaces import DroneAnomalyCreate


def get_anomalies_by_inspection_uuid(
    *, db: Session, inspection_uuid: uuid.UUID
) -> Sequence[DroneAnomaly]:
    """Get all anomalies for a given inspection from the project-specific
    schema.

    Args:
        db: TODO: describe.
        inspection_uuid: TODO: describe.
    """
    stmt = select(DroneAnomaly).where(DroneAnomaly.inspection_uuid == inspection_uuid)
    result = db.execute(stmt)
    return result.scalars().all()


def get_anomaly_count_by_inspection_uuid(
    *, db: Session, inspection_uuid: uuid.UUID
) -> int:
    """Get the count of anomalies for a given inspection from the
    project-specific schema.

    Args:
        db: TODO: describe.
        inspection_uuid: TODO: describe.
    """
    stmt = (
        select(func.count())
        .select_from(DroneAnomaly)
        .where(DroneAnomaly.inspection_uuid == inspection_uuid)
    )
    result = db.execute(stmt)
    return result.scalar_one()


def bulk_create_drone_anomalies_incremental(
    *,
    db: Session,
    anomalies_data: list[DroneAnomalyCreate],
    inspection_uuid: uuid.UUID,
):
    """Bulk insert new anomalies without deleting existing ones.

    Args:
        db: TODO: describe.
        anomalies_data: TODO: describe.
        inspection_uuid: TODO: describe.
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
    """Update drone anomalies with the event_id they are associated with.
    Note: This function does NOT commit the transaction - it should be called
    within an existing transaction.

    Args:
        db: TODO: describe.
        anomaly_uuids: TODO: describe.
        event_id: TODO: describe.
    """
    logging.info(
        "🔧 update_anomalies_with_event_id called: "
        f"event_id={event_id}, anomaly_uuids={anomaly_uuids}"
    )

    # First, check how many anomalies exist with these UUIDs
    stmt = (
        select(func.count())
        .select_from(DroneAnomaly)
        .where(DroneAnomaly.anomaly_uuid.in_(anomaly_uuids))
    )
    result = db.execute(stmt)
    existing_count = result.scalar_one()

    logging.info(
        "📊 Found "
        f"{existing_count} existing anomalies out of "
        f"{len(anomaly_uuids)} requested UUIDs"
    )

    # Update the anomalies using a more efficient bulk update
    update_stmt = (
        update(DroneAnomaly)
        .where(DroneAnomaly.anomaly_uuid.in_(anomaly_uuids))
        .values(event_id=event_id)
    )

    result = db.execute(update_stmt)

    logging.info(f"🔄 Updated {result.rowcount} anomalies with event_id {event_id}")  # type: ignore[attr-defined]

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
    """Get all anomalies for a given event from the project-specific schema.

    Args:
        db: TODO: describe.
        event_id: TODO: describe.
    """
    stmt = select(DroneAnomaly).where(DroneAnomaly.event_id == event_id)
    result = db.execute(stmt)
    return result.scalars().all()
