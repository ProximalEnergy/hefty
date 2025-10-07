from uuid import UUID

from core.enumerations import UserTypeEnum
from fastapi import Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.admin.user_permissions import get_user_permissions
from app._dependencies.authentication import get_user
from app.dependencies import get_async_db
from app.interfaces import UserAuthed


async def require_jwt_or_api_superadmin(*, user: UserAuthed = Depends(get_user)):
    """Require the user to be a superadmin or authenticated via JWT.
    This is helpful for UI-only routes which should not be accessible to users
    directly via the API."""
    if not (
        user.authentication_method == "jwt"
        or user.user_type_id == UserTypeEnum.SUPERADMIN
    ):
        raise HTTPException(
            status_code=403,
            detail="You must be a superadmin to access this resource",
        )


async def require_user_project(
    *,
    project_id: UUID = Path(...),
    user: UserAuthed = Depends(get_user),
):
    """Require the user to have access to the requested project."""
    if project_id not in user.operational_project_ids:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this project",
        )


async def require_user_projects(
    *,
    project_ids: list[UUID] = Query(...),
    user: UserAuthed = Depends(get_user),
):
    """Require the user to have access to all of the requested projects."""
    if not all(
        project_id in user.operational_project_ids for project_id in project_ids
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access these projects",
        )


def require_user_type(*, user_type_id: UserTypeEnum):
    """Require the user to have at least the specified user type."""

    async def dependency(*, user: UserAuthed = Depends(get_user)) -> None:
        if user.user_type_id > user_type_id:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions",
            )

    return dependency


def require_user_permissions(*, permission_ids: list[int]):
    """Require the user to have the specified permissions on the requested project."""

    async def dependency(
        *,
        db: AsyncSession = Depends(get_async_db),
        user: UserAuthed = Depends(get_user),
        project_id: UUID = Path(...),
    ) -> None:
        user_permissions = await get_user_permissions(
            db=db,
            user_ids=[user.user_id],
            project_ids=[project_id],
        )

        if (
            not all(
                user_permission.permission_id in permission_ids
                for user_permission in user_permissions
            )
            or not user_permissions
        ):
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions",
            )

    return dependency


async def require_user_company(
    *,
    company_id: UUID | None = Query(None),
    user: UserAuthed = Depends(get_user),
) -> UUID | None:
    """Require appropriate company access.
    - Superadmins (user_type_id == UserTypeEnum.SUPERADMIN) can access any
    company's data or all
      companies if company_id is None
    - Regular users must specify their own company_id and can only access their
      own company's data
    Returns the appropriate company_id to use for database filtering
    (None means all companies for superusers)."""

    # For superusers
    if user.user_type_id == UserTypeEnum.SUPERADMIN:
        return None

    # For regular users, use their company_id if not specified
    if company_id is None:
        company_id = user.company_id

    if company_id != user.company_id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this company's data",
        )

    return company_id
