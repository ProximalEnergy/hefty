import uuid
from typing import Annotated

from core.dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import interfaces
from app._crud.operational.report_instances import (
    bulk_upsert_report_instances,
)
from app.dependencies import (
    get_async_db,
    get_is_superadmin_async,
    requires_superadmin_async,
)

router = APIRouter(
    prefix="/projects/{project_id}/report-instances",
    tags=["project_report_instances"],
)


@router.get("", response_model=list[interfaces.ReportInstance])
def get_project_reports_instances(
    project_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    is_superadmin: Annotated[bool, Depends(get_is_superadmin_async)],
    report_type_ids: list[int] | None = None,
    deep: bool = False,
):
    if is_superadmin:
        is_visible = None
    else:
        is_visible = True

    report_instances = core.crud.project.reports.get_project_report_instances(
        db=db,
        project_id=project_id,
        is_visible=is_visible,
        report_type_ids=report_type_ids,
        deep=deep,
    ).models()

    return report_instances


@router.put(
    "",
    response_model=list[interfaces.ReportInstance],
    dependencies=[Depends(requires_superadmin_async)],
)
async def bulk_update_project_report_instances(
    project_id: uuid.UUID,
    data: interfaces.ReportInstancesBulkUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    """
    Bulk update report instances for a project.
    Only accessible by superadmins.
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
