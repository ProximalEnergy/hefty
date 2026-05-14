from typing import Literal

import sqlalchemy as sa
from core.db_query import DbQuery

from core import models


def get_root_causes_query(
    *,
    root_cause_ids: list[int] = [],
) -> DbQuery[models.RootCause, Literal[False]]:
    """Return a DbQuery for root causes.

    Args:
        root_cause_ids: Root cause ids to filter by.
    """
    stmt = sa.select(models.RootCause)
    if root_cause_ids:
        stmt = stmt.where(models.RootCause.root_cause_id.in_(root_cause_ids))
    return DbQuery(query=stmt)
