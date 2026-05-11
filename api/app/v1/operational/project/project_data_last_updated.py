from uuid import UUID

from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException

from app import interfaces
from app._crud.operational.project_data_last_updated import (
    get_project_data_last_updated,
)
from app._dependencies.authorization import require_user_project

router = APIRouter(
    prefix="/data-last-updated",
    tags=["project_data_last_updated"],
)


@router.get("", response_model=interfaces.ProjectDataLastUpdatedInterface)
async def get_project_data_last_updated_endpoint(
    project_id: UUID,
    _auth: None = Depends(require_user_project),
):
    """todo

    Args:
        project_id: Description for project_id.
    """
    last_updated = await get_project_data_last_updated(
        project_id=project_id,
    ).get_async(output_type=OutputType.SQLALCHEMY)

    if last_updated is None:
        raise HTTPException(
            status_code=404,
            detail="Project data last updated not found",
        )

    return last_updated
