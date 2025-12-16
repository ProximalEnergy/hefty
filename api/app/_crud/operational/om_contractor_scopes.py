from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_om_contractor_scopes_by_project(
    *,
    db: AsyncSession,
    project_id: UUID,
):
    """todo

    Args:
        db: TODO: describe.
        project_id: TODO: describe.
    """
    query = (
        select(
            models.OMContractorScope.om_contractor_scope_id,
            models.OMContractorScope.project_id,
            models.OMContractorScope.company_id,
            models.OMContractorScope.scope_json,
            models.OMContractorScope.contractor_addressee,
            models.OMContractorScope.contractor_email,
            models.OMContractorScope.contractor_phone,
            models.Company.name_short.label("company_name_short"),
            models.Company.name_long.label("company_name_long"),
        )
        .join(
            models.Company,
            models.OMContractorScope.company_id == models.Company.company_id,
        )
        .where(models.OMContractorScope.project_id == project_id)
    )

    result = await db.execute(query)
    return result.all()
