from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import delete, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies
from app._crud.operational.om_contractor_scopes import (
    get_om_contractor_scopes_by_project,
)
from app.dependencies import check_project_access_async
from core import models

router = APIRouter(
    prefix="/projects/{project_id}/om-contractors",
    tags=["project_om_contractors"],
    dependencies=[Depends(check_project_access_async)],
)


@router.get("")
async def get_project_om_contractor_scopes(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """todo

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
    """
    rows = await get_om_contractor_scopes_by_project(db=db, project_id=project_id)
    data = []
    for row in rows:
        m = row._mapping
        data.append(
            {
                "om_contractor_scope_id": m["om_contractor_scope_id"],
                "project_id": m["project_id"],
                "company_id": m["company_id"],
                "company_name_short": m.get("company_name_short"),
                "company_name_long": m.get("company_name_long"),
                "scope_json": m["scope_json"],
                "contractor_addressee": m.get("contractor_addressee"),
                "contractor_email": m.get("contractor_email"),
                "contractor_phone": m.get("contractor_phone"),
            }
        )
    return data


@router.post("")
async def create_project_om_contractor_scope(
    project_id: UUID,
    payload: dict,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """todo

    Args:
        project_id: TODO: describe.
        payload: TODO: describe.
        db: TODO: describe.
    """
    company_id = payload.get("company_id")
    scope_json = payload.get("scope_json") or {}
    contractor_addressee = payload.get("contractor_addressee")
    contractor_email = payload.get("contractor_email")
    contractor_phone = payload.get("contractor_phone")

    stmt = (
        insert(models.OMContractorScope)
        .values(
            project_id=project_id,
            company_id=company_id,
            scope_json=scope_json,
            contractor_addressee=contractor_addressee,
            contractor_email=contractor_email,
            contractor_phone=contractor_phone,
        )
        .returning(
            models.OMContractorScope.om_contractor_scope_id,
            models.OMContractorScope.project_id,
            models.OMContractorScope.company_id,
            models.OMContractorScope.scope_json,
            models.OMContractorScope.contractor_addressee,
            models.OMContractorScope.contractor_email,
            models.OMContractorScope.contractor_phone,
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    row = result.one()
    m = row._mapping
    return {
        "om_contractor_scope_id": m["om_contractor_scope_id"],
        "project_id": str(m["project_id"]),
        "company_id": str(m["company_id"]),
        "scope_json": m["scope_json"],
        "contractor_addressee": m.get("contractor_addressee"),
        "contractor_email": m.get("contractor_email"),
        "contractor_phone": m.get("contractor_phone"),
    }


@router.put("/{om_contractor_scope_id}")
async def update_project_om_contractor_scope(
    project_id: UUID,
    om_contractor_scope_id: int,
    payload: dict,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """todo

    Args:
        project_id: TODO: describe.
        om_contractor_scope_id: TODO: describe.
        payload: TODO: describe.
        db: TODO: describe.
    """
    scope_json = payload.get("scope_json") or {}
    contractor_addressee = payload.get("contractor_addressee")
    contractor_email = payload.get("contractor_email")
    contractor_phone = payload.get("contractor_phone")

    stmt = (
        update(models.OMContractorScope)
        .where(
            models.OMContractorScope.om_contractor_scope_id == om_contractor_scope_id,
            models.OMContractorScope.project_id == project_id,
        )
        .values(
            scope_json=scope_json,
            contractor_addressee=contractor_addressee,
            contractor_email=contractor_email,
            contractor_phone=contractor_phone,
        )
        .returning(
            models.OMContractorScope.om_contractor_scope_id,
            models.OMContractorScope.project_id,
            models.OMContractorScope.company_id,
            models.OMContractorScope.scope_json,
            models.OMContractorScope.contractor_addressee,
            models.OMContractorScope.contractor_email,
            models.OMContractorScope.contractor_phone,
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    row = result.one()
    m = row._mapping
    return {
        "om_contractor_scope_id": m["om_contractor_scope_id"],
        "project_id": str(m["project_id"]),
        "company_id": str(m["company_id"]),
        "scope_json": m["scope_json"],
        "contractor_addressee": m.get("contractor_addressee"),
        "contractor_email": m.get("contractor_email"),
        "contractor_phone": m.get("contractor_phone"),
    }


@router.delete("/{om_contractor_scope_id}")
async def delete_project_om_contractor_scope(
    project_id: UUID,
    om_contractor_scope_id: int,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """todo

    Args:
        project_id: TODO: describe.
        om_contractor_scope_id: TODO: describe.
        db: TODO: describe.
    """
    stmt = delete(models.OMContractorScope).where(
        models.OMContractorScope.om_contractor_scope_id == om_contractor_scope_id,
        models.OMContractorScope.project_id == project_id,
    )
    await db.execute(stmt)
    await db.commit()
    return {"status": "ok"}
