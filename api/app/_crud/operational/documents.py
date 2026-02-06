from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_project_documents(
    db: AsyncSession,
    *,
    document_ids: list[UUID] | None = None,
    project_ids: list[UUID] | None = None,
    company_ids: list[UUID] | None = None,
):
    """Get documents filtered by optional identifiers.

    Args:
        db: Database session.
        document_ids: Document identifiers to filter by.
        project_ids: Project identifiers to filter by.
        company_ids: Company identifiers to filter by.
    """
    query = select(models.Document)

    if document_ids:
        query = query.where(models.Document.document_id.in_(document_ids))
    if project_ids:
        query = query.where(models.Document.project_id.in_(project_ids))
    if company_ids:
        query = query.where(models.Document.company_id.in_(company_ids))

    result = await db.execute(query)
    return list(result.scalars().all())


async def create_project_document(
    db: AsyncSession,
    *,
    company_id: UUID,
    project_id: UUID,
    s3_key: str,
    openai_file_id: str,
):
    """Create a document record for a project.

    Args:
        db: Database session.
        company_id: Company identifier owning the document.
        project_id: Project identifier owning the document.
        s3_key: Storage key for the document.
        openai_file_id: OpenAI file identifier.
    """
    document = models.Document(
        company_id=company_id,
        project_id=project_id,
        s3_key=s3_key,
        openai_file_id=openai_file_id,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


async def delete_project_document(
    db: AsyncSession,
    *,
    document_id: UUID,
):
    """Delete a document by identifier.

    Args:
        db: Database session.
        document_id: Document identifier to delete.
    """
    delete_stmt = delete(models.Document).where(
        models.Document.document_id == document_id,
    )
    await db.execute(delete_stmt)
    await db.commit()
