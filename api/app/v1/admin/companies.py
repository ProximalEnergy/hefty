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
    """todo

    Args:
        company: TODO: describe.
        db: TODO: describe.
    """
    return await crud_create_company(db=db, company=company)


@router.get("")
async def get_companies(
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    company_ids: list[uuid.UUID] | None = Query(default=None),
    name_shorts: list[str] | None = Query(default=None),
):
    """todo

    Args:
        db: TODO: describe.
        company_ids: TODO: describe.
        name_shorts: TODO: describe.
    """
    companies = await crud_get_companies(
        db=db,
        company_ids=company_ids,
        name_shorts=name_shorts,
    )
    return companies
