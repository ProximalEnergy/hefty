from typing import Annotated
from uuid import UUID

from core.crud.operational.cmms_permissions import get_cmms_permissions_by_project_id
from core.db_query import OutputType
from fastapi import APIRouter, Depends

from app import interfaces
from app._dependencies.authentication import get_user
from app.interfaces import UserAuthed

router = APIRouter(
    prefix="/cmms-permissions",
    tags=["cmms-permissions"],
)


@router.get("", response_model=list[interfaces.CMMSPermissionInterface])
async def get_cmms_permissions(
    project_id: UUID,
    user: Annotated[UserAuthed, Depends(get_user)],
) -> list[interfaces.CMMSPermissionInterface]:
    """Get CMMS permissions for the project for the current user's company.

    Args:
        project_id: Operational project identifier used to scope CMMS permissions.
        user: Authenticated user context containing company membership.
    """
    cmms_permissions = await get_cmms_permissions_by_project_id(
        company_id=user.company_id,
        project_id=project_id,
        can_view=True,
    ).get_async(output_type=OutputType.SQLALCHEMY)

    return [
        interfaces.CMMSPermissionInterface.model_validate(cmms_permission)
        for cmms_permission, _ in cmms_permissions
    ]
