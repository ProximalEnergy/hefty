from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.users import create_api_key as crud_create_api_key
from app._crud.admin.users import delete_api_key as crud_delete_api_key

router = APIRouter(prefix="/api-key", tags=["api-key"])


@router.get("/", response_model=interfaces.APIKey, summary="Get API Key")
def get_api_key(
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    return {"api_key": user_data.api_key}


@router.post("/", summary="Create API Key")
async def create_api_key(
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_jwt_user_data_async)
    ],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    await crud_create_api_key(db, user_id=user_data.user_id)


@router.delete("/", summary="Delete API Key")
async def delete_api_key(
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    await crud_delete_api_key(db, user_id=user_data.user_id)
