from typing import Any
from uuid import UUID

from core.db_query import DbQuery, OutputType
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import get_logger
from core import models

logger = get_logger(name=__name__)


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
    existing_company_project = await DbQuery(
        query=select(models.CompanyProject).where(
            models.CompanyProject.company_id == company_id,
            models.CompanyProject.project_id == project_id,
        ),
        is_scalar=True,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )

    if existing_company_project:
        logger.info(f"Company project {company_id}|{project_id} already exists")
        return existing_company_project

    # Create vector store
    try:
        client = OpenAI()
        # Get company and project names for vector store naming
        row = await DbQuery[Any, Any](
            query=select(
                models.Company.name_short.label("company_name_short"),
                models.Project.name_short.label("project_name_short"),
            ).where(
                models.Company.company_id == company_id,
                models.Project.project_id == project_id,
            ),
            is_scalar=True,
        ).get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        )

        if row is None:
            raise ValueError("Company or project not found")

        vector_store_name = f"{row['company_name_short']}-{row['project_name_short']}"
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
