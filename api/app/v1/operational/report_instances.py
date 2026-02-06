import uuid
from typing import Annotated

from core.db_query import OutputType
from fastapi import APIRouter, Depends, Query

from app import interfaces
from app._crud.operational.report_instances import (
    get_report_instances as crud_get_report_instances,
)
from app._dependencies.filtering import filter_project_ids_to_user
from app.dependencies import get_is_superadmin_async

router = APIRouter(prefix="/report-instances", tags=["report_instances"])


@router.get(
    "",
    response_model=list[interfaces.ReportInstance],
    operation_id="get_report_instances",
)
async def get_report_instances(
    is_superadmin: Annotated[bool, Depends(get_is_superadmin_async)],
    project_ids: Annotated[
        list[uuid.UUID] | None,
        Depends(filter_project_ids_to_user),
    ],
    report_type_ids: Annotated[list[int] | None, Query()] = None,
    deep: bool = False,
):
    """todo

    Args:
        is_superadmin: Description for is_superadmin.
        project_ids: Description for project_ids.
        report_type_ids: Description for report_type_ids.
        deep: Description for deep.
    """
    if is_superadmin:
        is_visible = None
    else:
        is_visible = True

    query = crud_get_report_instances(
        project_ids=project_ids,
        is_visible=is_visible,
        report_type_ids=report_type_ids,
        deep=deep,
    )

    report_instances_df = await query.get_async(output_type=OutputType.POLARS)

    return report_instances_df.to_dicts()
