from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from app._crud.operational.project_data_last_updated import (
    get_project_data_last_updated,
)
from app.dependencies import check_project_access_async, get_async_db

router = APIRouter(
    prefix="/projects/{project_id}/data-last-updated",
    tags=["project_data_last_updated"],
    dependencies=[Depends(check_project_access_async)],
)


@router.get("", response_model=interfaces.ProjectDataLastUpdated)
async def get_project_data_last_updated_endpoint(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    """todo

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
    """
    last_updated = await get_project_data_last_updated(
        db=db,
        project_id=project_id,
    )

    if last_updated is None:
        raise HTTPException(
            status_code=404,
            detail="Project data last updated not found",
        )

    return last_updated
