from typing import Literal
from uuid import UUID

from core.db_query import DbQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


def get_project_data_last_updated(
    *, project_id: UUID
) -> DbQuery[models.ProjectDataLastUpdated, Literal[True]]:
    """Fetch the last-updated metadata for a single project.

    Args:
        project_id: Project identifier to retrieve update timestamps for.
    """
    query = (
        select(models.ProjectDataLastUpdated)
        .where(models.ProjectDataLastUpdated.project_id == project_id)
        .limit(1)
    )
    return DbQuery(query=query, is_scalar=True)


async def get_project_data_last_updateds(
    *, db: AsyncSession, project_ids: list[UUID]
) -> list[models.ProjectDataLastUpdated]:
    """Fetch last-updated metadata for multiple projects.

    Args:
        db: Async database session bound to the operational schema.
        project_ids: Collection of project IDs to include in the lookup.
    """
    result = await db.execute(
        select(models.ProjectDataLastUpdated).where(
            models.ProjectDataLastUpdated.project_id.in_(project_ids)
        )
    )
    return list(result.scalars().all())
