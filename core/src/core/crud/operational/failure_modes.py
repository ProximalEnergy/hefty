from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from core import models
from core.model_list import ModelList


def get_failure_modes(
    db: Session,
    *,
    failure_mode_ids: list[int] = [],
    return_query: bool = False,
) -> ModelList[models.FailureMode]:
    query = db.query(models.FailureMode)
    if failure_mode_ids:
        query = query.filter(models.FailureMode.failure_mode_id.in_(failure_mode_ids))
    return ModelList(query=query, return_query=return_query)


async def get_failure_modes_async(
    db: AsyncSession,
    *,
    failure_mode_ids: list[int] = [],
) -> Sequence[models.FailureMode]:
    """
    Retrieve a list of failure modes from the database.

    Args:
        db (AsyncSession): The database session to use for the query.
        failure_mode_ids (list[int], optional): A list of failure mode IDs
            to filter the results. Defaults to an empty list.

    Returns:
        list[models.FailureMode]: A list of failure modes matching the
            specified criteria.
    """
    stmt = sa.select(models.FailureMode)

    if failure_mode_ids:
        stmt = stmt.filter(models.FailureMode.failure_mode_id.in_(failure_mode_ids))

    result = await db.execute(stmt)
    return result.scalars().all()
