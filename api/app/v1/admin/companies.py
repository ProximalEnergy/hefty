import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.companies import create_company as crud_create_company
from app._crud.admin.companies import (
    get_companies as crud_get_companies,
)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=interfaces.Company)
async def create_company(
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


@router.get("")
async def get_companies(
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
