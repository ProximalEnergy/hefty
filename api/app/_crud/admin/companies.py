from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from core import models


async def get_companies(
    *,
    db: AsyncSession,
    company_ids: list[UUID] | None = None,
    name_shorts: list[str] | None = None,
):
    """Return companies filtered by IDs or short names.

    Args:
        db: Async SQLAlchemy session used for the query.
        company_ids: Optional list of company IDs to filter by.
        name_shorts: Optional list of company short names to filter by.
    """
    query = select(models.Company)

    if company_ids:
        query = query.where(models.Company.company_id.in_(company_ids))
    if name_shorts:
        query = query.where(models.Company.name_short.in_(name_shorts))

    result = await db.execute(query)
    return result.scalars().all()


async def create_company(
    *,
    db: AsyncSession,
    company: interfaces.CompanyCreate,
):
    # If a company with the same name_short already exists, return it
    """Create a company or return the existing record.

    Args:
        db: Async SQLAlchemy session used for the transaction.
        company: Input payload for the new company.
    """
    existing_result = await db.execute(
        select(models.Company).where(models.Company.name_short == company.name_short)
    )
    existing_company = existing_result.scalar_one_or_none()
    if existing_company:
        return existing_company

    # Otherwise, create a new company. Handle race conditions gracefully.
    db_company = models.Company(**company.model_dump())
    db.add(db_company)
    try:
        await db.commit()
    except IntegrityError:
        # Another request created the company concurrently. Roll back and fetch it.
        await db.rollback()
        retry_result = await db.execute(
            select(models.Company).where(
                models.Company.name_short == company.name_short,
            )
        )
        retry_company = retry_result.scalar_one_or_none()
        if retry_company is None:
            # Should not happen, but raise to surface the real issue
            raise
        return retry_company

    await db.refresh(db_company)
    return db_company
