import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.companies import create_company as crud_create_company
from app._crud.admin.companies import get_companies as crud_get_companies
from app._crud.admin.companies import (
    get_companies_with_projects as crud_get_companies_with_projects,
)
from app._dependencies.authentication import get_user

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post(
    "",
    response_model=interfaces.Company,
    operation_id="create_company",
)
async def create_company_route(
    *,
    company: interfaces.CompanyCreate,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Create a company.

    Args:
        company: Company payload to create.
        db: Async database session.
    """
    return await crud_create_company(db=db, company=company)


@router.get(
    "",
    operation_id="get_companies",
)
async def get_companies_route(
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    company_ids: list[uuid.UUID] | None = Query(default=None),
    name_shorts: list[str] | None = Query(default=None),
):
    """Get companies filtered by IDs or short names.

    Args:
        db: Async database session.
        company_ids: Optional company UUID filters.
        name_shorts: Optional short name filters.
    """
    companies = await crud_get_companies(
        db=db,
        company_ids=company_ids,
        name_shorts=name_shorts,
    )
    return companies


@router.get(
    "/with-projects",
    response_model=list[interfaces.CompanyWithProjects],
)
async def get_companies_with_projects_route(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    """Get companies with aggregated project IDs accessible to the user.

    Returns all companies that have at least one user with project access.
    Project lists are filtered to those the requesting user can also access.

    Args:
        db: Async database session.
        user_data: Authenticated user data from dependency.
    """
    return await crud_get_companies_with_projects(
        db=db,
        user_id=user_data.user_id,
    )
