from uuid import UUID

from core.crud.operational import qse_integrations as operational_qse_integrations
from core.db_query import OutputType
from core.enumerations import UserTypeEnum
from fastapi import Depends, HTTPException, Path, Query

from app import dependencies
from app._crud.admin.user_permissions import get_user_permissions
from app._dependencies.authentication import get_user
from app.interfaces import UserAuthed
from core import models


async def require_jwt_or_api_superadmin(*, user: UserAuthed = Depends(get_user)):
    """Require the user to be a superadmin or authenticated via JWT.
        This is helpful for UI-only routes which should not be accessible to users
        directly via the API.

    Args:
        user: Authenticated user payload to validate.
    """
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
    """Require the user to have access to the requested project.

    Args:
        project_id: Project UUID being requested.
        user: Authenticated user payload to validate.
    """
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
    """Require the user to have access to all of the requested projects.

    Args:
        project_ids: Project UUIDs being requested.
        user: Authenticated user payload to validate.
    """
    if not all(
        project_id in user.operational_project_ids for project_id in project_ids
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access these projects",
        )


def require_user_type(*, user_type_id: UserTypeEnum):
    """Require the user to have at least the specified user type.

    Args:
        user_type_id: Minimum user type required to access the resource.
    """

    async def dependency(*, user: UserAuthed = Depends(get_user)) -> None:
        """Validate the authenticated user meets the minimum user type.

        Args:
            user: Authenticated user payload to validate.
        """
        if user.user_type_id > user_type_id:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions",
            )

    return dependency


def require_user_permissions(*, permission_ids: list[int]):
    """Require the user to have the specified permissions on the requested project.

    Args:
        permission_ids: Permission IDs required to access the resource.
    """

    async def dependency(
        *,
        user: UserAuthed = Depends(get_user),
        project_id: UUID = Path(...),
    ) -> None:
        """Validate the user has permission on the requested project.

        Args:
            user: Authenticated user payload to validate.
            project_id: Project UUID being requested.
        """
        user_permissions_df = await get_user_permissions(
            user_ids=[user.user_id],
            project_ids=[project_id],
        ).get_async(output_type=OutputType.PANDAS)

        if user_permissions_df.empty or not set(permission_ids).issubset(
            user_permissions_df["permission_id"]
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
        (None means all companies for superusers).

    Args:
        company_id: Company UUID to access, or None to indicate all.
        user: Authenticated user payload to validate.
    """

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


async def require_qse_integration_with_view_permission(
    *,
    project: models.Project = Depends(dependencies.get_project_api),
    user: UserAuthed = Depends(get_user),
) -> models.QSEIntegration:
    """Load project QSE integration and require company can_view permission.

    Args:
        project: Project whose QSE integration is required.
        user: Authenticated user whose company permissions are checked.
    """
    qse_integration_query = (
        operational_qse_integrations.get_qse_integration_by_project_id(
            project_id=project.project_id,
        )
    )
    qse_integration = await qse_integration_query.get_async(
        output_type=OutputType.SQLALCHEMY,
    )
    if qse_integration is None:
        raise HTTPException(status_code=404, detail="QSE integration not found")

    permissions_query = operational_qse_integrations.get_qse_permissions_by_company_id(
        company_id=user.company_id,
    )
    permissions = await permissions_query.get_async(
        output_type=OutputType.SQLALCHEMY,
    )
    has_permission = any(
        perm.qse_integration_id == qse_integration.qse_integration_id and perm.can_view
        for perm in permissions
    )
    if not has_permission:
        raise HTTPException(status_code=403, detail="Forbidden")
    return qse_integration
