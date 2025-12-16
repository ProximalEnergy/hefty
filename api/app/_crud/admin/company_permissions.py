from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from core import models


async def get_company_permissions(
    *,
    db: AsyncSession,
    company_id: UUID,
    project_id: UUID,
) -> list[models.CompanyPermission]:
    """todo

    Args:
        db: TODO: describe.
        company_id: TODO: describe.
        project_id: TODO: describe.
    """
    query = select(models.CompanyPermission)
    query = query.where(models.CompanyPermission.company_id == company_id)
    query = query.where(models.CompanyPermission.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars().all())
