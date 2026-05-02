import uuid
from typing import Annotated
from uuid import UUID

from core.db_query import OutputType
from core.enumerations import ReportTypeEnum
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import core
from app import interfaces
from app._crud.operational.report_instances import (
    bulk_upsert_report_instances,
)
from app._dependencies import authentication
from app.dependencies import (
    get_async_db,
    get_is_superadmin_async,
    requires_superadmin_async,
)
from app.interfaces import UserAuthed

SABLE_POINT_COMPANY_ID = UUID("38a8e696-dafa-44c0-b817-e3aee8cdfe8c")


router = APIRouter(
    prefix="/report-instances",
    tags=["project_report_instances"],
)


@router.get("", response_model=list[interfaces.ReportInstanceInterface])
async def get_project_reports_instances(
    project_id: uuid.UUID,
    is_superadmin: Annotated[bool, Depends(get_is_superadmin_async)],
    user: Annotated[UserAuthed, Depends(authentication.get_user)],
    report_type_ids: list[int] | None = None,
    deep: bool = False,
):
    """todo

    Args:
        project_id: Description for project_id.
        is_superadmin: Description for is_superadmin.
        user: Description for user.
        report_type_ids: Description for report_type_ids.
        deep: Description for deep.
    """
    if is_superadmin:
        is_visible = None
    else:
        is_visible = True

    query = core.crud.project.reports.get_project_report_instances(
        project_id=project_id,
        is_visible=is_visible,
        report_type_ids=report_type_ids,
        deep=deep,
    )

    report_instances = await query.get_async(output_type=OutputType.SQLALCHEMY)

    # Remove the EEC report instance if you are a Sable Point user.
    if user.company_id == SABLE_POINT_COMPANY_ID:
        report_instances = [
            ri
            for ri in report_instances
            if ri.report_type_id != ReportTypeEnum.EEC_BESS_MONTHLY_REPORT
        ]

    return report_instances


@router.put(
    "",
    response_model=list[interfaces.ReportInstanceInterface],
    dependencies=[Depends(requires_superadmin_async)],
)
async def bulk_update_project_report_instances(
    project_id: uuid.UUID,
    data: interfaces.ReportInstancesBulkUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    """Bulk update report instances for a project.
        Only accessible by superadmins.

    Args:
        project_id: Description for project_id.
        data: Description for data.
        db: Description for db.
    """
    try:
        report_instances_data = [
            {
                "report_type_id": instance.report_type_id,
                "is_visible": instance.is_visible,
            }
            for instance in data.report_instances
        ]

        updated_instances = await bulk_upsert_report_instances(
            db=db,
            project_id=project_id,
            report_instances=report_instances_data,
            report_type_ids_to_delete=data.report_type_ids_to_delete,
        )

        # Load report_type relationships

        for instance in updated_instances:
            await db.refresh(instance, ["report_type"])

        return updated_instances
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update report instances: {str(e)}",
        )
