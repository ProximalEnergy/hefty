from typing import Annotated

from core.crud.operational.user_project_labels import (
    get_user_project_labels_by_user_id_and_project_id,
)
from core.db_query import OutputType
from fastapi import APIRouter, Depends

from app.dependencies import get_project_api, get_user_data_async
from app.interfaces import Project, UserData, UserProjectLabel
from app.v1.operational.user_project_labels import (
    UserProjectLabel,
    _build_user_project_labels,
    _validate_project_access,
)

router = APIRouter(prefix="/user-project-labels", tags=["user_project_labels"])


@router.get("", response_model=list[UserProjectLabel])
async def get_user_project_labels_by_project_id(
    project: Annotated[Project, Depends(get_project_api)],
    user: Annotated[UserData, Depends(get_user_data_async)],
):
    """Get all labels for a specific project (for the requesting user).

    Args:
        project: Project object to query labels for.
        user: Authenticated user data.
    """
    _validate_project_access(user=user, project_ids=[project.project_id])

    labels_query = get_user_project_labels_by_user_id_and_project_id(
        user_id=user.user_id,
        project_id=project.project_id,
    )
    labels = await labels_query.get_async(output_type=OutputType.SQLALCHEMY)
    return await _build_user_project_labels(
        user_id=user.user_id,
        labels=labels,
    )
