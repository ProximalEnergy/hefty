import datetime

from sqlalchemy.orm import Session

from core import models
from core.model_list import ModelList


def get_project_data_expected(
    project_db: Session,
    *,
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: list[int],
    expected_metric_ids: list[int] | None = None,
    return_query: bool = False,
) -> ModelList[models.DataExpected]:
    """
    Retrieve project expected data within a specified time range and for given devices.

    Args:
        project_db (Session): The database session to use for the query.
        start (datetime.datetime): The start time for filtering the data, inclusive.
        end (datetime.datetime): The end time for filtering the data, exclusive.
        device_ids (list[int]): A list of device IDs to filter the expected data.
        expected_metric_ids (Optional[list[int]], optional): A list of expected metric IDs to filter the data. Defaults to None.

    Returns:
        list[models.DataExpected]: A list of expected data records matching the criteria.
    """
    query = project_db.query(models.DataExpected)

    query = query.where(models.DataExpected.time >= start)
    query = query.where(models.DataExpected.time < end)
    query = query.where(models.DataExpected.device_id.in_(device_ids))

    if expected_metric_ids:
        query = query.where(
            models.DataExpected.expected_metric_id.in_(expected_metric_ids),
        )

    return ModelList(query=query, return_query=return_query)
