from typing import Literal
from uuid import UUID

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_company_permissions(
    *,
    company_id: UUID,
    project_id: UUID,
) -> DbQuery[models.CompanyPermission, Literal[False]]:
    """Get company permissions for a project.

    Args:
        company_id: Company identifier to filter permissions.
        project_id: Project identifier to filter permissions.
    """
    query = select(models.CompanyPermission).where(
        models.CompanyPermission.company_id == company_id,
        models.CompanyPermission.project_id == project_id,
    )
    return DbQuery(query=query)
