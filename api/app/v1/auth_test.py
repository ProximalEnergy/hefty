from uuid import UUID

from core.enumerations import UserTypeEnum
from fastapi import APIRouter, Depends, Path

from app._dependencies import authentication, authorization
from app.interfaces import UserAuthed

router = APIRouter(prefix="/auth", tags=["auth-test"])


@router.get("")
def get_auth(user: UserAuthed = Depends(authentication.get_user)):
    """todo

    Args:
        user: TODO: describe.
    """
    return {"user": user}


@router.get(
    "/require-admin",
    dependencies=[
        Depends(authorization.require_user_type(user_type_id=UserTypeEnum.ADMIN))
    ],
)
def get_auth_require_admin(user: UserAuthed = Depends(authentication.get_user)):
    """todo

    Args:
        user: TODO: describe.
    """
    return {"user": user}


@router.get(
    "/require-superadmin",
    dependencies=[
        Depends(authorization.require_user_type(user_type_id=UserTypeEnum.SUPERADMIN))
    ],
)
def get_auth_require_superadmin(
    user: UserAuthed = Depends(authentication.get_user),
):
    """todo

    Args:
        user: TODO: describe.
    """
    return {"user": user}


@router.get(
    "/require-jwt-or-api-superadmin",
    dependencies=[Depends(authorization.require_jwt_or_api_superadmin)],
)
def get_auth_require_jwt_or_api_superadmin(
    user: UserAuthed = Depends(authentication.get_user),
):
    """todo

    Args:
        user: TODO: describe.
    """
    return {"user": user}


@router.get(
    "/require-user-permission/{project_id}",
    dependencies=[
        Depends(authorization.require_user_permissions(permission_ids=[1])),
        Depends(authorization.require_user_project),
    ],
)
def get_auth_require_user_permission(
    user: UserAuthed = Depends(authentication.get_user),
    project_id: UUID = Path(...),
):
    """todo

    Args:
        user: TODO: describe.
        project_id: TODO: describe.
    """
    return {"user": user, "project_id": project_id}
