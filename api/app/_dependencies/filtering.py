from uuid import UUID

from core.enumerations import UserTypeEnum
from fastapi import Depends, Query

from app._dependencies.authentication import get_user
from app.interfaces import UserAuthed


async def filter_project_ids_to_user(
    *,
    project_ids: list[UUID] | None = Query(None),
    user: UserAuthed = Depends(get_user),
) -> list[UUID] | None:
    """Filter project IDs to those the user is allowed to access.

    Args:
        project_ids: TODO: describe.
        user: TODO: describe.
    """
    if user.user_type_id == UserTypeEnum.SUPERADMIN:
        return project_ids

    if project_ids is None:
        return list(user.operational_project_ids)

    allowed = set(user.operational_project_ids)
    return [project_id for project_id in project_ids if project_id in allowed]
