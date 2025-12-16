import datetime

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
    query = db.query(models.DataExpected)
    if device_ids:
        query = query.filter(models.DataExpected.device_id.in_(device_ids))
    if expected_metric_ids:
        query = query.filter(
            models.DataExpected.expected_metric_id.in_(expected_metric_ids)
        )
    query = query.filter(models.DataExpected.time.between(start, end))
    return query.all()
