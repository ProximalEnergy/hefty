from typing import Annotated
from uuid import UUID

from core.crud.admin.company_projects import (
    get_company_projects as crud_get_company_projects,
)
from core.db_query import OutputType
from fastapi import APIRouter, Depends

from app import interfaces
from app._dependencies import authorization
from app._dependencies.authentication import get_user

router = APIRouter(prefix="/company-projects", tags=["company-projects"])


@router.get(
    "/projects/{project_id}",
    dependencies=[Depends(authorization.require_user_project)],
    response_model=list[interfaces.CompanyProjectInterface],
)
async def get_company_projects_route(
    project_id: UUID,
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
) -> list[interfaces.CompanyProjectInterface]:
    """Get company-project records for the requesting user's company.

    Args:
        project_id: Operational project UUID.
        user_data: Authenticated user context.
    """
    df = await crud_get_company_projects(
        company_ids=[user_data.company_id],
        project_ids=[project_id],
    ).get_async(output_type=OutputType.POLARS)
    return [
        interfaces.CompanyProjectInterface.model_validate(item)
        for item in df.to_dicts()
    ]


@router.get(
    "/projects/{project_id}/all-companies",
    dependencies=[Depends(authorization.require_user_project)],
    response_model=list[interfaces.CompanyProjectInterface],
)
async def get_all_company_projects_for_project(
    project_id: UUID,
) -> list[interfaces.CompanyProjectInterface]:
    """Get all companies with access to a project.

        This endpoint is used by the event chat visibility dropdown to show
        which companies can see messages posted to the project.

    Args:
        project_id: Operational project UUID.
    """
    # Don't filter by company - get all companies for this project
    df = await crud_get_company_projects(
        company_ids=None,
        project_ids=[project_id],
    ).get_async(output_type=OutputType.POLARS)
    return [
        interfaces.CompanyProjectInterface.model_validate(item)
        for item in df.to_dicts()
    ]
