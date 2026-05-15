import uuid
from typing import Annotated
from uuid import UUID

import polars as pl
from core.db_query import OutputType
from core.enumerations import ReportTypeEnum
from fastapi import APIRouter, Depends, Query

from app import interfaces
from app._crud.operational.report_instances import (
    get_report_instances as crud_get_report_instances,
)
from app._dependencies.authentication import get_user
from app._dependencies.filtering import filter_project_ids_to_user
from app.dependencies import get_is_superadmin_async
from app.interfaces import UserAuthed

_EEC_BESS_MONTHLY_VISIBLE_COMPANY_IDS = frozenset(
    {
        UUID("01959294-3e51-4d3e-9f57-e9c2c3635c84"),  # Proximal
        UUID("a04594f8-9ee7-4916-80df-84a0dc9cb27d"),  # Excelsior
    }
)

router = APIRouter(prefix="/report-instances", tags=["report_instances"])


@router.get(
    "",
    response_model=list[interfaces.ReportInstanceInterface],
    operation_id="get_report_instances",
)
async def get_report_instances_route(
    is_superadmin: Annotated[bool, Depends(get_is_superadmin_async)],
    project_ids: Annotated[
        list[uuid.UUID] | None,
        Depends(filter_project_ids_to_user),
    ],
    user: Annotated[UserAuthed, Depends(get_user)],
    report_type_ids: Annotated[list[int] | None, Query()] = None,
    deep: bool = False,
):
    """
    Retrieve report instances for a given set of project IDs and report type IDs.

    Returns a list of report instances filtered by the user's permissions and, where
    applicable, restricts access to certain report types based on the user's company.

    Args:
        is_superadmin (bool): Whether the requesting user is a superadmin. Superadmins
            can view all report instances, visible or not.
        project_ids (list[UUID] | None): List of project UUIDs the request should be
            filtered to, further filtered to those the user has access to. If None,
            apply based on user's accessible projects.
        user (UserAuthed): The current authenticated user making the request.
        report_type_ids (list[int] | None): Optional list of report type IDs to filter
            the report instances by. report instances. If None, includes all report
            types.
        deep (bool): If True, fetches report instances with additional nested data.

    Returns:
        list[dict]: List of report instances (as dictionaries) matching the filters.
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

    if user.company_id not in _EEC_BESS_MONTHLY_VISIBLE_COMPANY_IDS:
        report_instances_df = report_instances_df.filter(
            pl.col("report_type_id") != ReportTypeEnum.EEC_BESS_MONTHLY_REPORT.value
        )

    return report_instances_df.to_dicts()
