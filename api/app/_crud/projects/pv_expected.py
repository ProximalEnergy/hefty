import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models


def get_pv_expected(
    *,
    db: Session,
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: list[int] | None = [],
    expected_metric_ids: list[int] | None = [],
):
    """Fetch expected PV data filtered by time, device, and metric.

    Args:
        db: Database session for the project schema.
        start: Inclusive start timestamp for the query window.
        end: Inclusive end timestamp for the query window.
        device_ids: Optional list of device IDs to filter.
        expected_metric_ids: Optional list of expected metric IDs to filter.
    """
    stmt = select(models.DataExpected)
    if device_ids:
        stmt = stmt.where(models.DataExpected.device_id.in_(device_ids))
    if expected_metric_ids:
        stmt = stmt.where(
            models.DataExpected.expected_metric_id.in_(expected_metric_ids)
        )
    stmt = stmt.where(models.DataExpected.time.between(start, end))
    result = db.execute(stmt)
    return result.scalars().all()
