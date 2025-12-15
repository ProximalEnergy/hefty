from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.company_projects import (
    get_company_projects as crud_get_company_projects,
)

router = APIRouter(prefix="/company-projects", tags=["company-projects"])


@router.get(
    "/projects/{project_id}",
    dependencies=[Depends(dependencies.check_project_access_async)],
    response_model=list[interfaces.CompanyProject],
)
async def get_company_projects(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    """todo

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
        user_data: TODO: describe.
    """
    return await crud_get_company_projects(
        db=db,
        company_ids=[user_data.company_id],
        project_ids=[project_id],
    )


@router.get(
    "/projects/{project_id}/all-companies",
    dependencies=[Depends(dependencies.check_project_access_async)],
    response_model=list[interfaces.CompanyProject],
)
async def get_all_company_projects_for_project(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    """Get all companies with access to a project.

        This endpoint is used by the event chat visibility dropdown to show
        which companies can see messages posted to the project.

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
        user_data: TODO: describe.
    """
    return await crud_get_company_projects(
        db=db,
        company_ids=None,  # Don't filter by company - get all companies for this project
        project_ids=[project_id],
    )
