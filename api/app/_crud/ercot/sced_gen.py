import datetime
from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_ercot_sced_gen(
    *,
    resource_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
) -> DbQuery[models.SCEDGen, Literal[False]]:
    """Build SCED generation query for a resource within a time range.

    Args:
        resource_id: ERCOT resource ID to filter by.
        start: Inclusive start timestamp for the query window.
        end: Exclusive end timestamp for the query window.
    """
    query = (
        select(models.SCEDGen)
        .where(models.SCEDGen.resource_id == resource_id)
        .where(models.SCEDGen.time >= start)
        .where(models.SCEDGen.time < end)
    )
    return DbQuery(query=query)
