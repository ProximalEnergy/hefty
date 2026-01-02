import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
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
    """TODO: add description.

    Args:
        db: TODO: describe.
        failure_mode_ids: TODO: describe.
        return_query: TODO: describe.
    """
    query = db.query(models.FailureMode)
    if failure_mode_ids:
        query = query.filter(models.FailureMode.failure_mode_id.in_(failure_mode_ids))
    return ModelList(query=query, return_query=return_query)


async def get_failure_modes_async(
    *,
    db: AsyncSession,
    failure_mode_ids: list[int] = [],
    return_query: bool = False,
) -> ModelList[models.FailureMode]:
    """
    Retrieve failure modes from the database as a ModelList.

    Args:
        db (AsyncSession): The database session to use for the query.
        failure_mode_ids (list[int], optional): A list of failure mode IDs
            to filter the results. Defaults to an empty list.
        return_query (bool, optional): If True, returns ModelList with
            unexecuted query for use with polars_dataframe_async().
            Defaults to False.

    Returns:
        ModelList[models.FailureMode]: A ModelList that can be converted
            to a list of models via .models() or to a polars DataFrame
            via await .polars_dataframe_async().

    Example:
        # Get as list of models
        ml = await get_failure_modes_async(
            db=db, failure_mode_ids=[1, 2, 3]
        )
        failure_modes = ml.models()

        # Get as polars DataFrame
        ml = await get_failure_modes_async(
            db=db, failure_mode_ids=[1, 2, 3], return_query=True
        )
        df = await ml.polars_dataframe_async()
    """
    stmt = sa.select(models.FailureMode)

    if failure_mode_ids:
        stmt = stmt.where(models.FailureMode.failure_mode_id.in_(failure_mode_ids))

    if return_query:
        # Return ModelList with TextClause for polars execution
        compiled = stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
        text_clause = text(str(compiled))
        return ModelList(query=text_clause)
    else:
        # Execute immediately and return ModelList with items
        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return ModelList.from_items(items)
