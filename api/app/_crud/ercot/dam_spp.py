import datetime
from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_ercot_dam_spp(
    *,
    settlement_point_ids: list[int] | None = None,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> DbQuery[models.DAMSPP, Literal[False]]:
    """Fetch DAM settlement point prices with optional filters.

    Args:
        settlement_point_ids: Settlement point IDs to filter by.
        start: Inclusive start timestamp for filtering.
        end: Exclusive end timestamp for filtering.
    """
    query = select(models.DAMSPP)

    if settlement_point_ids:
        query = query.where(
            models.DAMSPP.settlement_point_id.in_(settlement_point_ids),
        )
    if start:
        query = query.where(models.DAMSPP.time >= start)
    if end:
        query = query.where(models.DAMSPP.time < end)

    return DbQuery(query=query)
