from uuid import UUID

from sqlalchemy import select

from core import models
from core.db_query import DbQuery


def get_company_projects(
    *,
    company_ids: list[UUID] | None = None,
    project_ids: list[UUID] | None = None,
    vector_store_ids: str | None = None,
) -> DbQuery[models.CompanyProject]:
    """Get company projects by filters.

    Args:
        company_ids: List of company IDs.
        project_ids: List of project IDs.
        vector_store_ids: Vector store ID filter.
    """
    query = select(models.CompanyProject)

    if company_ids:
        query = query.where(models.CompanyProject.company_id.in_(company_ids))
    if project_ids:
        query = query.where(models.CompanyProject.project_id.in_(project_ids))
    if vector_store_ids:
        query = query.where(
            models.CompanyProject.vector_store_id.in_(vector_store_ids),
        )

    return DbQuery(query=query)
