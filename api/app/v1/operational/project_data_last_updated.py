from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from app._crud.operational.project_data_last_updated import (
    get_project_data_last_updateds,
)
from app._dependencies.authorization import require_user_projects
from app.dependencies import get_async_db

router = APIRouter(
    prefix="/project-data-last-updated",
    tags=["project_data_last_updated"],
)


@router.get(
    "",
    response_model=list[interfaces.ProjectDataLastUpdatedInterface],
    dependencies=[Depends(require_user_projects)],
)
async def get_project_data_last_updated_endpoint_route(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    project_ids: Annotated[list[UUID], Query()] = [],
):
    """todo

    Args:
        db: Description for db.
        project_ids: Description for project_ids.
    """
    last_updated = await get_project_data_last_updateds(
        db=db,
        project_ids=project_ids,
    )

    return last_updated
