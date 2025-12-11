import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.companies import create_company as crud_create_company
from app._crud.admin.companies import (
    get_companies as crud_get_companies,
)
from app._crud.admin.companies import (
    search_companies as crud_search_companies,
)

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=interfaces.Company)
async def create_company(
    *,
    company: interfaces.CompanyCreate,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    return await crud_create_company(db=db, company=company)


@router.get("")
async def get_companies(
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    company_ids: list[uuid.UUID] | None = Query(default=None),
    name_shorts: list[str] | None = Query(default=None),
):
    companies = await crud_get_companies(
        db=db,
        company_ids=company_ids,
        name_shorts=name_shorts,
    )
    return companies


@router.get("/search")
async def search_companies(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    q: str = Query(min_length=3),
    limit: int = 20,
):
    return await crud_search_companies(db=db, q=q, limit=limit)
