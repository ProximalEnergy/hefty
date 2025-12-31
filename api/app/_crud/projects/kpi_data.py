import datetime
from uuid import UUID

from sqlalchemy import select
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
    stmt = select(
        models.OperationalKPIData.kpi_type_id,
        models.OperationalKPIData.date,
        models.OperationalKPIData.project_data,
    )
    stmt = stmt.where(models.OperationalKPIData.project_id == project_id)
    stmt = stmt.where(models.OperationalKPIData.kpi_type_id.in_(kpi_type_ids))
    stmt = stmt.where(models.OperationalKPIData.date >= start.date())
    stmt = stmt.where(models.OperationalKPIData.date < end.date())
    result = db.execute(stmt)
    return result.all()
