from typing import Annotated

from core.crud.admin.users import get_user_by_id as crud_get_user
from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.users import create_api_key as crud_create_api_key
from app._crud.admin.users import delete_api_key as crud_delete_api_key
from app._dependencies.authentication import get_user

router = APIRouter(prefix="/api-key", tags=["api-key"])


@router.get("", response_model=interfaces.APIKey, summary="Get API Key")
async def get_api_key(
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    """Return the current user's API key.

    Args:
        user_data: Requesting user context.
    """

    user = await crud_get_user(user_id=user_data.user_id).get_async(
        output_type=OutputType.SQLALCHEMY
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"api_key": user.api_key}


@router.post(
    "",
    summary="Create API Key",
    operation_id="create_api_key",
)
async def create_api_key_route(
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_jwt_user_data_async)
    ],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Create an API key for the requesting user.

    Args:
        user_data: Requesting user context.
        db: Async database session.
    """
    await crud_create_api_key(db, user_id=user_data.user_id)


@router.delete("", summary="Delete API Key")
async def delete_api_key_route(
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Delete the API key for the requesting user.

    Args:
        user_data: Requesting user context.
        db: Async database session.
    """
    await crud_delete_api_key(db, user_id=user_data.user_id)
