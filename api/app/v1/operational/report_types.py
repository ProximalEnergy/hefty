from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import app._crud.operational.report_types as _crud
from app import interfaces
from app.dependencies import get_async_db

router = APIRouter(prefix="/report-types", tags=["report_types"])


@router.get(
    "",
    response_model=list[interfaces.ReportTypeInterface],
    operation_id="get_report_types",
)
async def get_report_types_route(
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    """todo

    Args:
        db: Description for db.
    """
    return await _crud.get_report_types(db=db)


@router.get(
    "/{report_type_id}",
    response_model=interfaces.ReportTypeInterface,
    operation_id="get_report_type_by_id",
)
async def get_report_type_route(
    report_type_id: int, db: Annotated[AsyncSession, Depends(get_async_db)]
):
    """todo

    Args:
        report_type_id: Description for report_type_id.
        db: Description for db.
    """
    return await _crud.get_report_type(db=db, report_type_id=report_type_id)
