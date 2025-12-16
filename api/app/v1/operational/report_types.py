from typing import Annotated

from core.dependencies import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import app._crud.operational.report_types as _crud
from app import interfaces
from app.dependencies import get_async_db

router = APIRouter(prefix="/report-types", tags=["report_types"])
deprecated_router = APIRouter(
    prefix="/report-types", tags=["report_types"], deprecated=True
)


@router.get(
    "",
    response_model=list[interfaces.ReportType],
    operation_id="get_report_types",
)
async def get_report_types(
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    """todo

    Args:
        db: TODO: describe.
    """
    return await _crud.get_report_types(db=db)


@deprecated_router.get(
    "",
    response_model=list[interfaces.ReportType],
    operation_id="get_report_types_legacy",
)
def get_report_types_legacy(*, db: Annotated[AsyncSession, Depends(get_db)]):
    """todo

    Args:
        db: TODO: describe.
    """
    return get_report_types(db=db)


@router.get(
    "/{report_type_id}",
    response_model=interfaces.ReportType,
    operation_id="get_report_type_by_id",
)
async def get_report_type(
    report_type_id: int, db: Annotated[AsyncSession, Depends(get_async_db)]
):
    """todo

    Args:
        report_type_id: TODO: describe.
        db: TODO: describe.
    """
    return await _crud.get_report_type(db=db, report_type_id=report_type_id)


@deprecated_router.get(
    "/{report_type_id}",
    response_model=interfaces.ReportType,
    operation_id="get_report_type_by_id_legacy",
)
def get_report_type_legacy(
    *, report_type_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    """todo

    Args:
        report_type_id: TODO: describe.
        db: TODO: describe.
    """
    return get_report_type(report_type_id, db)
