from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_project_data_last_updated(*, db: AsyncSession, project_id: UUID):
    """Fetch the last-updated metadata for a single project.

    Args:
        db: Async database session bound to the operational schema.
        project_id: Project identifier to retrieve update timestamps for.
    """
    result = await db.execute(
        select(models.ProjectDataLastUpdated).filter(
            models.ProjectDataLastUpdated.project_id == project_id
        )
    )
    return result.scalars().first()


async def get_project_data_last_updateds(*, db: AsyncSession, project_ids: list[UUID]):
    """Fetch last-updated metadata for multiple projects.

    Args:
        db: Async database session bound to the operational schema.
        project_ids: Collection of project IDs to include in the lookup.
    """
    result = await db.execute(
        select(models.ProjectDataLastUpdated).filter(
            models.ProjectDataLastUpdated.project_id.in_(project_ids)
        )
    )
    return result.scalars().all()
