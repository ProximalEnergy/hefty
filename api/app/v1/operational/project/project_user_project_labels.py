from typing import Annotated

from core.crud.operational.user_project_labels import (
    get_user_project_labels_by_user_id_and_project_id,
)
from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException

from app._dependencies.authentication import get_user
from app.dependencies import get_project_api
from app.interfaces import ProjectInterface, UserAuthed, UserProjectLabelInterface
from app.v1.operational.user_project_labels import _build_user_project_labels

router = APIRouter(prefix="/user-project-labels", tags=["user_project_labels"])


@router.get("", response_model=list[UserProjectLabelInterface])
async def get_user_project_labels_by_project_id(
    project: Annotated[ProjectInterface, Depends(get_project_api)],
    user: Annotated[UserAuthed, Depends(get_user)],
):
    """Get all labels for a specific project (for the requesting user).

    Args:
        project: Project object to query labels for.
        user: Authenticated user data.
    """
    if project.project_id not in user.operational_project_ids:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this project",
        )

    labels_query = get_user_project_labels_by_user_id_and_project_id(
        user_id=user.user_id,
        project_id=project.project_id,
    )
    labels = await labels_query.get_async(output_type=OutputType.SQLALCHEMY)
    return await _build_user_project_labels(
        user_id=user.user_id,
        labels=labels,
    )
