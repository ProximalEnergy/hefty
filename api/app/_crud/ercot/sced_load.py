import datetime
from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_ercot_sced_load(
    *,
    resource_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
) -> DbQuery[models.SCEDLoad, Literal[False]]:
    """Fetch SCED load records for a resource within a time range.

    Args:
        resource_id: ERCOT resource ID to filter by.
        start: Inclusive start timestamp for the query window.
        end: Exclusive end timestamp for the query window.
    """
    query = (
        select(models.SCEDLoad)
        .where(models.SCEDLoad.resource_id == resource_id)
        .where(models.SCEDLoad.time >= start)
        .where(models.SCEDLoad.time < end)
    )
    return DbQuery(query=query, use_scalars=True)
