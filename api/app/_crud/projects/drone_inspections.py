from core.models import DroneInspection

from app.interfaces import DroneInspectionCreate


def create_drone_inspection(*, db, inspection_data: DroneInspectionCreate):
    # Check if the inspection already exists in the project-specific schema
    """todo

    Args:
        db: TODO: describe.
        inspection_data: TODO: describe.
    """
    existing_inspection = (
        db.query(DroneInspection)
        .filter_by(inspection_uuid=inspection_data.inspection_uuid)
        .first()
    )
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
    return (
        db.query(DroneInspection).order_by(DroneInspection.inspection_time.desc()).all()
    )
