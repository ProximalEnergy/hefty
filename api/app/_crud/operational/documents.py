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
    """todo

    Args:
        db: TODO: describe.
        document_ids: TODO: describe.
        project_ids: TODO: describe.
        company_ids: TODO: describe.
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
    """todo

    Args:
        db: TODO: describe.
        company_id: TODO: describe.
        project_id: TODO: describe.
        s3_key: TODO: describe.
        openai_file_id: TODO: describe.
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
    """todo

    Args:
        db: TODO: describe.
        document_id: TODO: describe.
    """
    delete_stmt = delete(models.Document).where(
        models.Document.document_id == document_id,
    )
    await db.execute(delete_stmt)
    await db.commit()
