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
    """todo

    Args:
        db: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        device_ids: TODO: describe.
        expected_metric_ids: TODO: describe.
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
