import datetime
from typing import Literal

from sqlalchemy import select

from core import models
from core.db_query import DbQuery


def get_project_data_expected(
    *,
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: list[int],
    expected_metric_ids: list[int] | None = None,
) -> DbQuery[models.DataExpected, Literal[False]]:
    """
    Retrieve project expected data within a specified time range and for given devices.

    Args:
        start (datetime.datetime): The start time for filtering the data, inclusive.
        end (datetime.datetime): The end time for filtering the data, exclusive.
        device_ids (list[int]): A list of device IDs to filter the expected data.
        expected_metric_ids (Optional[list[int]], optional): A list of expected
            metric IDs to filter the data. Defaults to None.

    Returns:
        DbQuery[models.DataExpected, Literal[False]]: Query wrapper for expected
            data records matching the criteria.
    """
    stmt = select(models.DataExpected)
    stmt = stmt.where(models.DataExpected.time >= start)
    stmt = stmt.where(models.DataExpected.time < end)
    stmt = stmt.where(models.DataExpected.device_id.in_(device_ids))

    if expected_metric_ids:
        stmt = stmt.where(
            models.DataExpected.expected_metric_id.in_(expected_metric_ids),
        )

    return DbQuery(query=stmt)
