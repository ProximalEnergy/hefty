from core.models import DroneInspection
from sqlalchemy import select

from app.interfaces import DroneInspectionCreate


def create_drone_inspection(*, db, inspection_data: DroneInspectionCreate):
    # Check if the inspection already exists in the project-specific schema
    """todo

    Args:
        db: TODO: describe.
        inspection_data: TODO: describe.
    """
    stmt = select(DroneInspection).where(
        DroneInspection.inspection_uuid == inspection_data.inspection_uuid
    )
    result = db.execute(stmt)
    existing_inspection = result.scalar_one_or_none()
    if existing_inspection:
        return existing_inspection

    db_inspection = DroneInspection(**inspection_data.model_dump())
    db.add(db_inspection)
    db.commit()
    db.refresh(db_inspection)
    return db_inspection


def get_drone_inspections(*, db):
    """Get all drone inspections for a project from the project-specific schema.

    Args:
        db: TODO: describe.
    """
    stmt = select(DroneInspection).order_by(DroneInspection.inspection_time.desc())
    result = db.execute(stmt)
    return result.scalars().all()
