from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from core import models


async def get_companies_with_projects(
    *,
    db: AsyncSession,
    user_id: str,
) -> list[interfaces.CompanyWithProjects]:
    """Return companies with aggregated project IDs from user_projects.

    Args:
        db: Async SQLAlchemy session.
        user_id: Requesting user ID used to filter accessible projects.
    """
    user_accessible_projects_subquery = (
        select(models.UserProject.operational_project_id)
        .where(models.UserProject.user_id == user_id)
        .subquery()
    )

    query = (
        select(
            models.Company.company_id,
            models.Company.name_short,
            models.Company.name_long,
            func.array_agg(
                func.distinct(models.UserProject.operational_project_id)
            ).label("project_ids"),
        )
        .join(models.User, models.Company.company_id == models.User.company_id)
        .join(models.UserProject, models.User.user_id == models.UserProject.user_id)
        .where(
            models.UserProject.operational_project_id.in_(
                select(user_accessible_projects_subquery)
            )
        )
        .group_by(
            models.Company.company_id,
            models.Company.name_short,
            models.Company.name_long,
        )
        .order_by(models.Company.name_short)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        interfaces.CompanyWithProjects(
            company_id=row.company_id,
            name_short=row.name_short,
            name_long=row.name_long,
            project_ids=row.project_ids or [],
        )
        for row in rows
    ]


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
