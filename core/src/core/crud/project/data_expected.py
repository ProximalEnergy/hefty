import datetime
from collections.abc import Sequence
from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_project_data_expected(
    *,
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: Sequence[int] | None = None,
    expected_metric_ids: Sequence[int] | None = None,
) -> DbQuery[models.DataExpected, Literal[False]]:
    """
    Retrieve project expected data within a specified time range and for given devices.

    Args:
        start (datetime.datetime): The start time for filtering the data, inclusive.
        end (datetime.datetime): The end time for filtering the data, exclusive.
        device_ids (Sequence[int]): Device IDs to filter the expected data.
            Defaults to None, which will return data for all devices.
        expected_metric_ids (Sequence[int]): Expected metric IDs to filter the data.
            Defaults to None, which will return data for all expected metrics.

    Returns:
        DbQuery[models.DataExpected, Literal[False]]: Query wrapper for expected
            data records matching the criteria.
    """
    stmt = select(models.DataExpected)
    stmt = stmt.where(models.DataExpected.time >= start)
    stmt = stmt.where(models.DataExpected.time < end)

    if device_ids:
        stmt = stmt.where(models.DataExpected.device_id.in_(device_ids))

    if expected_metric_ids:
        stmt = stmt.where(
            models.DataExpected.expected_metric_id.in_(expected_metric_ids),
        )

    return DbQuery(query=stmt)
