from typing import Literal

import sqlalchemy as sa
from core.db_query import DbQuery

from core import models


def get_failure_modes(
    *,
    failure_mode_ids: list[int] = [],
) -> DbQuery[models.FailureMode, Literal[False]]:
    """Return a DbQuery for failure modes.

    Args:
        failure_mode_ids: Failure mode ids to filter by.
    """
    stmt = sa.select(models.FailureMode)
    if failure_mode_ids:
        stmt = stmt.where(models.FailureMode.failure_mode_id.in_(failure_mode_ids))
    return DbQuery(query=stmt)


async def get_failure_modes_async(
    *,
    failure_mode_ids: list[int] = [],
) -> DbQuery[models.FailureMode, Literal[False]]:
    return get_failure_modes(failure_mode_ids=failure_mode_ids)
