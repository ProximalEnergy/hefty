import uuid
from typing import Annotated

from core.dependencies import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import core
from app import interfaces
from app.dependencies import get_is_superadmin_async

router = APIRouter(
    prefix="/projects/{project_id}/report-instances",
    tags=["project_report_instances"],
)


@router.get("/", response_model=list[interfaces.ReportInstance])
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
