from typing import Annotated
from uuid import UUID

from core.crud.admin.company_projects import (
    get_company_projects as crud_get_company_projects,
)
from core.db_query import OutputType
from fastapi import APIRouter, Depends

from app import dependencies, interfaces

router = APIRouter(prefix="/company-projects", tags=["company-projects"])


@router.get(
    "/projects/{project_id}",
    dependencies=[Depends(dependencies.check_project_access_async)],
    response_model=list[interfaces.CompanyProject],
)
async def get_company_projects(
    project_id: UUID,
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
) -> list[interfaces.CompanyProject]:
    """todo

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
        user_data: TODO: describe.
    """
    df = await crud_get_company_projects(
        company_ids=[user_data.company_id],
        project_ids=[project_id],
    ).get_async(output_type=OutputType.POLARS)
    return [interfaces.CompanyProject.model_validate(item) for item in df.to_dicts()]


@router.get(
    "/projects/{project_id}/all-companies",
    dependencies=[Depends(dependencies.check_project_access_async)],
    response_model=list[interfaces.CompanyProject],
)
async def get_all_company_projects_for_project(
    project_id: UUID,
) -> list[interfaces.CompanyProject]:
    """Get all companies with access to a project.

        This endpoint is used by the event chat visibility dropdown to show
        which companies can see messages posted to the project.

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
        user_data: TODO: describe.
    """
    # Don't filter by company - get all companies for this project
    df = await crud_get_company_projects(
        company_ids=None,
        project_ids=[project_id],
    ).get_async(output_type=OutputType.POLARS)
    return [interfaces.CompanyProject.model_validate(item) for item in df.to_dicts()]
