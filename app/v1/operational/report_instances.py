import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from app._crud.operational.report_instances import (
    get_report_instances as crud_get_report_instances,
)
from app.dependencies import get_async_db, get_is_superadmin_async

router = APIRouter(prefix="/report-instances", tags=["report_instances"])


@router.get(
    "/",
    response_model=list[interfaces.ReportInstance],
    operation_id="get_report_instances",
)
async def get_report_instances(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    is_superadmin: Annotated[bool, Depends(get_is_superadmin_async)],
    project_ids: Annotated[list[uuid.UUID] | None, Query()] = [],
    report_type_ids: Annotated[list[int] | None, Query()] = [],
    deep: bool = False,
):
    if is_superadmin:
        is_visible = None
    else:
        is_visible = True

    report_instances = await get_report_instances_helper(
        db=db,
        is_visible=is_visible,
        project_ids=project_ids,
        report_type_ids=report_type_ids,
        deep=deep,
    )

    return report_instances


async def get_report_instances_helper(
    *,
    db: AsyncSession,
    is_visible: bool | None,
    report_type_ids: list[int] | None = None,
    project_ids: list[uuid.UUID] | None = None,
    deep: bool = False,
):
    project_ids = project_ids if project_ids and len(project_ids) > 0 else None
    report_type_ids = (
        report_type_ids if report_type_ids and len(report_type_ids) > 0 else None
    )
    report_instances = await crud_get_report_instances(
        db=db,
        project_ids=project_ids,
        is_visible=is_visible,
        report_type_ids=report_type_ids,
        deep=deep,
    )

    return report_instances
