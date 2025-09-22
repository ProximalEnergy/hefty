from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies
from app._crud.admin.users import get_users as crud_get_users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/")
async def get_users(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        dependencies.interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    users = await crud_get_users(db=db, company_ids=[user_data.company_id])

    # Process each user tuple and add operational_project_ids
    users_with_project_ids = [
        {
            **{k: v for k, v in user[0].__dict__.items() if k != "api_key"},
            "operational_project_ids": user[1],
        }
        for user in users
    ]

    return users_with_project_ids
