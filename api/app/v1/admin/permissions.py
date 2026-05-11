import uuid
from typing import Annotated

from core.db_query import OutputType
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.company_permissions import (
    get_company_permissions as crud_get_company_permissions,
)
from app._crud.admin.permissions import get_permissions as crud_get_permissions
from app._crud.admin.user_permissions import (
    create_user_permission as crud_create_user_permission,
)
from app._crud.admin.user_permissions import (
    delete_user_permission as crud_delete_user_permission,
)
from app._crud.admin.user_permissions import (
    get_user_permissions as crud_get_user_permissions,
)
from app._crud.admin.user_projects import (
    get_users_with_project_access as crud_get_users_with_project_access,
)
from app._dependencies import authorization
from app._dependencies.authentication import get_user
from core import models

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get(
    "",
    response_model=list[interfaces.PermissionInterface],
    dependencies=[Depends(dependencies.requires_admin_async)],
    summary="Get all permissions",
)
async def get_all_permissions():
    """Get all available permissions in the system. Requires admin access.

    Args:
        None.
    """
    permissions_df = await crud_get_permissions(
        permission_ids=None,
    ).get_async(output_type=OutputType.PANDAS)
    return permissions_df.to_dict(orient="records")


@router.get(
    "/projects/{project_id}/user",
    response_model=list[interfaces.PermissionInterface],
    dependencies=[Depends(authorization.require_user_project)],
    summary="Get user permissions by project",
)
async def get_user_permissions_route(
    project_id: uuid.UUID,
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    """Get all permissions for the requesting user at a given project.

    Args:
        project_id: Project id to query.
        user_data: Requesting user context.
    """

    # Get user_permission objects
    user_permissions_df = await crud_get_user_permissions(
        user_ids=[user_data.user_id],
        project_ids=[project_id],
    ).get_async(output_type=OutputType.PANDAS)

    # Identify permission IDs from user_permission objects
    permission_ids = user_permissions_df["permission_id"].tolist()

    if not permission_ids:
        return []

    # Get permission objects
    permissions_df = await crud_get_permissions(
        permission_ids=permission_ids,
    ).get_async(output_type=OutputType.PANDAS)

    return permissions_df.to_dict(orient="records")


class UserPermissionRequest(BaseModel):
    """Payload for adding or removing a user permission."""

    permission_id: int


@router.post(
    "/projects/{project_id}/users/{user_id}",
    response_model=interfaces.UserPermissionInterface,
    dependencies=[
        Depends(authorization.require_user_project),
        Depends(dependencies.requires_admin_async),
    ],
)
async def add_user_permission(
    project_id: uuid.UUID,
    user_id: str,
    user_permission: UserPermissionRequest,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Add a user permission for a user at a project. Requires admin access.

    Args:
        project_id: Project id to modify.
        user_id: User id to modify.
        user_permission: Permission payload.
        db: Async database session.
    """

    # Create a user_permission object
    user_permission_model = models.UserPermission(
        permission_id=user_permission.permission_id,
        project_id=project_id,
        user_id=user_id,
    )

    # Create the user_permission in the database
    await crud_create_user_permission(db=db, user_permission=user_permission_model)

    # Return the created user_permission
    return user_permission_model


@router.delete(
    "/projects/{project_id}/users/{user_id}",
    response_model=interfaces.UserPermissionInterface,
    operation_id="delete_user_permission",
    dependencies=[
        Depends(authorization.require_user_project),
        Depends(dependencies.requires_admin_async),
    ],
)
async def delete_user_permission_route(
    project_id: uuid.UUID,
    user_id: str,
    user_permission: UserPermissionRequest,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Delete a user permission for a user at a project. Requires admin access.

    Args:
        project_id: Project id to modify.
        user_id: User id to modify.
        user_permission: Permission payload.
        db: Async database session.
    """

    # Create a user_permission object
    user_permission_model = models.UserPermission(
        permission_id=user_permission.permission_id,
        project_id=project_id,
        user_id=user_id,
    )

    # Delete the user_permission from the database
    await crud_delete_user_permission(db=db, user_permission=user_permission_model)

    # Return the deleted user_permission
    return user_permission_model


@router.get(
    "/projects/{project_id}/company",
    response_model=list[interfaces.PermissionInterface],
    dependencies=[Depends(authorization.require_user_project)],
    summary="Get company permissions by project",
)
async def get_company_permissions_route(
    project_id: uuid.UUID,
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    """Get all permissions for the requesting user's company at a given project.

    Args:
        project_id: Project id to query.
        user_data: Requesting user context.
    """

    # Get company permissions data
    company_permissions_df = await crud_get_company_permissions(
        company_id=user_data.company_id,
        project_id=project_id,
    ).get_async(output_type=OutputType.PANDAS)

    # Identify permission IDs from company permissions data
    if company_permissions_df.empty:
        return []

    permission_ids = company_permissions_df["permission_id"].tolist()

    if not permission_ids:
        return []

    # Get permission objects
    permissions_df = await crud_get_permissions(
        permission_ids=permission_ids,
    ).get_async(output_type=OutputType.PANDAS)

    return permissions_df.to_dict(orient="records")


@router.get(
    "/projects/{project_id}/company-users",
    response_model=list[interfaces.UserWithPermissions],
    dependencies=[
        Depends(authorization.require_user_project),
        Depends(dependencies.requires_admin_async),
    ],
    summary="Get company users with permissions by project",
)
async def get_users_permissions(
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    """Get all users, and their permissions, with access to a given project
        for the requesting user's company. Requires admin access.

    Args:
        project_id: Project id to query.
        db: Async database session.
        user_data: Requesting user context.
    """

    # Get users with access to the project
    users = await crud_get_users_with_project_access(
        db=db,
        company_id=user_data.company_id,
        project_id=project_id,
    )

    # Get all user_permission objects for the users with access to the project
    user_permissions_df = await crud_get_user_permissions(
        user_ids=[user.user_id for user in users],
        project_ids=[project_id],
    ).get_async(output_type=OutputType.PANDAS)

    # Create a mapping of user IDs to their permission IDs
    user_id_to_permission_ids: dict[str, list[int]] = {}
    if not user_permissions_df.empty:
        user_id_to_permission_ids = {
            str(user_id): [int(permission_id) for permission_id in permission_ids]
            for user_id, permission_ids in user_permissions_df.groupby("user_id")[
                "permission_id"
            ]
            .apply(list)
            .to_dict()
            .items()
        }

    return [
        interfaces.UserWithPermissions(
            user_id=user.user_id,
            name_long=user.name_long or "",
            permission_ids=user_id_to_permission_ids.get(user.user_id, []),
        )
        for user in users
    ]
