from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_project_data_last_updated(*, db: AsyncSession, project_id: UUID):
    result = await db.execute(
        select(models.ProjectDataLastUpdated).filter(
            models.ProjectDataLastUpdated.project_id == project_id
        )
    )
    return result.scalars().first()


async def get_project_data_last_updateds(*, db: AsyncSession, project_ids: list[UUID]):
    result = await db.execute(
        select(models.ProjectDataLastUpdated).filter(
            models.ProjectDataLastUpdated.project_id.in_(project_ids)
        )
    )
    return result.scalars().all()
