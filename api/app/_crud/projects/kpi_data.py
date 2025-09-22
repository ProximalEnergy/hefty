import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from core import models


def get_project_kpi_summary(
    db: Session,
    *,
    project_id: UUID,
    kpi_type_ids: list[int],
    start: datetime.datetime,
    end: datetime.datetime,
):
    """Get KPI summary data for a project within a date range.

    Args:
        db: Database session
        project_id: UUID of the project
        kpi_type_ids: List of KPI type IDs to query
        start: Start datetime (inclusive)
        end: End datetime (exclusive)
    """
    return (
        db.query(
            models.OperationalKPIData.kpi_type_id,
            models.OperationalKPIData.date,
            models.OperationalKPIData.project_data,
        )
        .filter(models.OperationalKPIData.project_id == project_id)
        .filter(models.OperationalKPIData.kpi_type_id.in_(kpi_type_ids))
        .filter(models.OperationalKPIData.date >= start.date())
        .filter(models.OperationalKPIData.date < end.date())
        .all()
    )
