from typing import Literal
from uuid import UUID

from core.db_query import DbQuery, OutputType
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from core import models


def query_companies_with_projects(*, user_id: str) -> DbQuery:
    """Build company/project aggregate query filtered by requesting user access.

    Args:
        user_id: Requesting user ID for accessible project filtering.
    """
    accessible_projects_query = (
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
                select(accessible_projects_query)
            )
        )
        .group_by(
            models.Company.company_id,
            models.Company.name_short,
            models.Company.name_long,
        )
        .order_by(models.Company.name_short)
    )
    return DbQuery(query=query)


def query_companies(
    *,
    company_ids: list[UUID] | None = None,
    name_shorts: list[str] | None = None,
) -> DbQuery[models.Company, Literal[False]]:
    """Build company query filtered by IDs or short names.

    Args:
        company_ids: Optional company UUID filters.
        name_shorts: Optional short name filters.
    """
    query = select(models.Company)

    if company_ids:
        query = query.where(models.Company.company_id.in_(company_ids))
    if name_shorts:
        query = query.where(models.Company.name_short.in_(name_shorts))

    return DbQuery(query=query)


def query_company_by_name_short(
    *,
    name_short: str,
) -> DbQuery[models.Company, Literal[True]]:
    """Build scalar company query by company short name.

    Args:
        name_short: Company short name used for exact matching.
    """
    query = select(models.Company).where(models.Company.name_short == name_short)
    return DbQuery(query=query, is_scalar=True)


async def get_companies_with_projects(
    *,
    db: AsyncSession,
    user_id: str,
) -> list[interfaces.CompanyWithProjects]:
    """Return companies with aggregated project IDs from user projects.

    Args:
        db: Async SQLAlchemy session.
        user_id: Requesting user ID for accessible project filtering.
    """
    rows = await query_companies_with_projects(user_id=user_id).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )

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
        db: Async SQLAlchemy session.
        company_ids: Optional company UUID filters.
        name_shorts: Optional short name filters.
    """
    return await query_companies(
        company_ids=company_ids,
        name_shorts=name_shorts,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )


async def create_company(
    *,
    db: AsyncSession,
    company: interfaces.CompanyCreate,
):
    """Create a company or return the existing record.

    Args:
        db: Async SQLAlchemy session.
        company: Input payload for the company to create.
    """
    existing_company = await query_company_by_name_short(
        name_short=company.name_short
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    if existing_company:
        return existing_company

    db_company = models.Company(**company.model_dump())
    db.add(db_company)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        retry_company = await query_company_by_name_short(
            name_short=company.name_short
        ).get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        )
        if retry_company is None:
            raise
        return retry_company

    await db.refresh(db_company)
    return db_company
