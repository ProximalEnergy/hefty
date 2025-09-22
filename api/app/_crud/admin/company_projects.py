import logging
from uuid import UUID

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models

logger = logging.getLogger(__name__)


async def get_company_projects(
    db: AsyncSession,
    *,
    company_ids: list[UUID] | None = None,
    project_ids: list[UUID] | None = None,
    vector_store_ids: str | None = None,
):
    query = select(models.CompanyProject)

    if company_ids:
        query = query.where(models.CompanyProject.company_id.in_(company_ids))
    if project_ids:
        query = query.where(models.CompanyProject.project_id.in_(project_ids))
    if vector_store_ids:
        query = query.where(
            models.CompanyProject.vector_store_id.in_(vector_store_ids),
        )

    result = await db.execute(query)
    return list(result.scalars().all())


async def create_company_project(
    *,
    db: AsyncSession,
    company_id: UUID,
    project_id: UUID,
) -> models.CompanyProject:
    """
    Create a new CompanyProject record with a vector store.

    Args:
        db: The SQLAlchemy database session.
        company_id: The company ID.
        project_id: The project ID.

    Returns:
        The newly created CompanyProject object.
    """
    # Check if company project already exists
    existing_query = select(models.CompanyProject).where(
        models.CompanyProject.company_id == company_id,
        models.CompanyProject.project_id == project_id,
    )
    existing_result = await db.execute(existing_query)
    existing_company_project = existing_result.scalar_one_or_none()

    if existing_company_project:
        logger.info(f"Company project {company_id}|{project_id} already exists")
        return existing_company_project

    # Create vector store
    try:
        client = OpenAI()
        # Get company and project names for vector store naming
        company_query = select(models.Company).where(
            models.Company.company_id == company_id
        )
        project_query = select(models.Project).where(
            models.Project.project_id == project_id
        )

        company_result = await db.execute(company_query)
        project_result = await db.execute(project_query)

        company = company_result.scalar_one_or_none()
        project = project_result.scalar_one_or_none()

        if not company or not project:
            raise ValueError("Company or project not found")

        vector_store_name = f"{company.name_short}-{project.name_short}"
        vector_store = client.vector_stores.create(name=vector_store_name)
        vector_store_id = vector_store.id

        logger.info(f"Created vector store: {vector_store_id} for {vector_store_name}")

    except Exception as e:
        logger.error(f"Failed to create vector store: {e}")
        raise ValueError(f"Failed to create vector store: {e}")

    # Create CompanyProject record
    company_project = models.CompanyProject(
        company_id=company_id,
        project_id=project_id,
        vector_store_id=vector_store_id,
    )

    db.add(company_project)
    await db.commit()
    await db.refresh(company_project)

    logger.info(f"Created company project {company_id}|{project_id}|{vector_store_id}")
    return company_project
