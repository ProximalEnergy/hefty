import uuid
from typing import Annotated

from core.enumerations import UserTypeEnum
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.users import create_user as create_user_crud
from app._crud.admin.users import delete_user as delete_user_crud
from app._crud.admin.users import get_users as crud_get_users
from app._utils.user_management import (
    create_clerk_user,
    delete_clerk_user,
    send_onboarding_email,
    update_clerk_user_theme,
)
from app.interfaces import User, UserCreate

router = APIRouter(prefix="/users", tags=["users"])


class ThemeUpdateRequest(BaseModel):
    theme: str
    vite_environment: str


@router.get(
    "/",
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def get_users(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    company_ids: list[uuid.UUID] | None = Query(default=None),
    user_ids: list[str] | None = Query(default=None),
):
    users = await crud_get_users(db=db, company_ids=company_ids, user_ids=user_ids)

    # Process each user tuple and add operational_project_ids
    users_with_project_ids = [
        {
            **{k: v for k, v in user[0].__dict__.items() if k != "api_key"},
            "operational_project_ids": user[1],
        }
        for user in users
    ]

    return users_with_project_ids


@router.get(
    "/self",
)
async def get_self(
    user_data: Annotated[dict, Depends(dependencies.get_user_data_async)],
):
    return user_data


@router.post(
    "/create-with-clerk",
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def create_user(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: UserCreate,
):
    # Create user in Clerk
    new_user_data = await create_clerk_user(
        user=user,
        company_name_short=user.company_name_short,
    )

    # Check if the user was created in Clerk successfully
    if "error" in new_user_data:
        raise HTTPException(status_code=400, detail=new_user_data["error"])

    # Create user in database
    await create_user_crud(
        db=db,
        user=User(
            user_id=new_user_data["user_id"],
            user_type_id=UserTypeEnum.USER,
            company_id=user.company_id,
            name_long=user.first_name + " " + user.last_name,
            api_key=None,
        ),
    )

    # Send onboarding email to user
    await send_onboarding_email(
        email=user.email,
        name=user.first_name,
        password=new_user_data["password"],
    )


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_id: str,
):
    await delete_clerk_user(user_id=user_id)
    await delete_user_crud(db=db, user_id=user_id)


@router.put(
    "/self/clerk-theme",
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
async def update_self_clerk_theme(
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
    request: ThemeUpdateRequest,
):
    """Update the current user's theme in Clerk."""
    user_id = user_data.user_id
    return await update_clerk_user_theme(
        user_id=user_id,
        theme=request.theme,
        vite_environment=request.vite_environment,
    )
