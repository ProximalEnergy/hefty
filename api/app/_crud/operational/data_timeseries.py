import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_operational_data_timeseries(
    db: AsyncSession,
    *,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project_ids: list[UUID] | None = None,
):
    """
    Retrieve data from the operational.data_timeseries table.

    Args:
        db (AsyncSession): The database session to use for the query.
        start (Optional[datetime.datetime]): The start time for filtering the
            timeseries data.
        end (Optional[datetime.datetime]): The end time for filtering the
            timeseries data.
        project_ids (Optional[list[UUID]]): A list of project IDs to filter the
            timeseries data.

    Returns:
        list[models.OperationalDataTimeseries]: A list of operational data timeseries
            records that match the filters.
    """
    query = select(models.OperationalDataTimeseries)

    if start:
        query = query.where(models.OperationalDataTimeseries.time >= start)
    if end:
        query = query.where(models.OperationalDataTimeseries.time < end)
    if project_ids:
        query = query.where(
            models.OperationalDataTimeseries.project_id.in_(project_ids),
        )

    result = await db.execute(query)
    return list(result.scalars().all())
