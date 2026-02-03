import uuid
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.company_permissions import (
    get_company_permissions as crud_get_company_permissions,
)
from app._crud.admin.permissions import (
    get_permissions as crud_get_permissions,
)
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
from core import models
from core.db_query import OutputType

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get(
    "",
    response_model=list[interfaces.Permission],
    dependencies=[Depends(dependencies.requires_admin_async)],
    summary="Get all permissions",
)
async def get_all_permissions(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Get all available permissions in the system. Requires admin access.

    Args:
        db: TODO: describe.
    """
    permissions = await crud_get_permissions(db=db, permission_ids=None)
    return permissions


@router.get(
    "/projects/{project_id}/user",
    response_model=list[interfaces.Permission],
    dependencies=[Depends(dependencies.check_project_access_async)],
    summary="Get user permissions by project",
)
async def get_user_permissions(
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    """Get all permissions for the requesting user at a given project.

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
        user_data: TODO: describe.
    """

    # Get user_permission objects
    user_permissions = await crud_get_user_permissions(
        db=db,
        user_ids=[user_data.user_id],
        project_ids=[project_id],
    )

    # Identify permission IDs from user_permission objects
    permission_ids = [u_p.permission_id for u_p in user_permissions]

    # Get permission objects
    permissions = await crud_get_permissions(db=db, permission_ids=permission_ids)

    return permissions


class UserPermissionRequest(BaseModel):
    """todo"""

    permission_id: int


@router.post(
    "/projects/{project_id}/users/{user_id}",
    response_model=interfaces.UserPermission,
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def add_user_permission(
    project_id: uuid.UUID,
    user_id: str,
    user_permission: UserPermissionRequest,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Add a user permission for a user at a project. Requires admin access.

    Args:
        project_id: TODO: describe.
        user_id: TODO: describe.
        user_permission: TODO: describe.
        db: TODO: describe.
    """

    # NOTE: We are omitting any project access checks here
    # because that is handled whenever a user requests data for a specific project

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
    response_model=interfaces.UserPermission,
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def delete_user_permission(
    project_id: uuid.UUID,
    user_id: str,
    user_permission: UserPermissionRequest,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Delete a user permission for a user at a project. Requires admin access.

    Args:
        project_id: TODO: describe.
        user_id: TODO: describe.
        user_permission: TODO: describe.
        db: TODO: describe.
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
    response_model=list[interfaces.Permission],
    dependencies=[Depends(dependencies.check_project_access_async)],
    summary="Get company permissions by project",
)
async def get_company_permissions(
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    """Get all permissions for the requesting user's company at a given project.

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
        user_data: TODO: describe.
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

    # Get permission objects
    permissions = await crud_get_permissions(db=db, permission_ids=permission_ids)

    return permissions


@router.get(
    "/projects/{project_id}/company-users",
    response_model=list[interfaces.UserWithPermissions],
    dependencies=[
        Depends(dependencies.check_project_access_async),
        Depends(dependencies.requires_admin_async),
    ],
    summary="Get company users with permissions by project",
)
async def get_users_permissions(
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    """Get all users, and their permissions, with access to a given project
        for the requesting user's company. Requires admin access.

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
        user_data: TODO: describe.
    """

    # Get users with access to the project
    users = await crud_get_users_with_project_access(
        db=db,
        company_id=user_data.company_id,
        project_id=project_id,
    )

    # Get all user_permission objects for the users with access to the project
    user_permissions = await crud_get_user_permissions(
        db=db,
        user_ids=[user.user_id for user in users],
        project_ids=[project_id],
    )

    # Create a mapping of user IDs to their permission IDs
    user_id_to_permission_ids: dict[str, list[int]] = defaultdict(list)
    for user_permission in user_permissions:
        user_id_to_permission_ids[user_permission.user_id].append(
            user_permission.permission_id,
        )

    # Add permission IDs to each user object
    for user in users:
        user.permission_ids = user_id_to_permission_ids.get(user.user_id, [])  # type: ignore

    return users
