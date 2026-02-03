import asyncio
import uuid
from typing import Annotated

from core.crud.admin.users import get_users as get_users_core
from core.db_query import OutputType
from core.enumerations import UserTypeEnum
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.users import create_user as create_user_crud
from app._crud.admin.users import delete_user as delete_user_crud
from app._utils.user_management import (
    create_clerk_user,
    delete_clerk_user,
    get_clerk_user_image_url,
    send_onboarding_email,
    update_clerk_user_demo_mode,
    update_clerk_user_theme,
)
from app.interfaces import User, UserCreate

router = APIRouter(prefix="/users", tags=["users"])


class ThemeUpdateRequest(BaseModel):
    """Request body for updating the user's theme preferences in Clerk."""

    theme: str
    vite_environment: str


class DemoModeUpdateRequest(BaseModel):
    """Request body for toggling demo mode flags for a Clerk user."""

    demo_mode: bool
    vite_environment: str


@router.get(
    "",
    dependencies=[Depends(dependencies.requires_admin_async)],
    response_model=list[interfaces.UserWithProjects],
)
async def get_users(
    company_ids: list[uuid.UUID] | None = Query(default=None),
    user_ids: list[str] | None = Query(default=None),
    include_image_urls: bool = Query(
        default=False, description="Include user profile image URLs from Clerk"
    ),
):
    """List users along with their operational project assignments.

    Args:
        company_ids: Optional list of companies to scope returned users.
        user_ids: Optional list of Clerk user IDs to filter by.
        include_image_urls: Whether to request profile images from Clerk.
    """
    users = await get_users_core(company_ids=company_ids, user_ids=user_ids).get_async(
        output_type=OutputType.PANDAS
    )

    project_ids_by_user = (
        users.dropna(subset=["project_ids"])
        .groupby("user_id")["project_ids"]
        .unique()
        .apply(list)
    )
    base_users = users.drop(columns=["project_ids"]).drop_duplicates("user_id")
    if "api_key" in base_users.columns:
        base_users = base_users.drop(columns=["api_key"])
    base_users["operational_project_ids"] = base_users["user_id"].map(
        project_ids_by_user
    )
    base_users["operational_project_ids"] = base_users["operational_project_ids"].apply(
        lambda value: value if isinstance(value, list) else []
    )

    users_with_project_ids = base_users.to_dict(orient="records")

    # Only fetch profile picture URL from Clerk if explicitly requested.
    # This avoids unnecessary API calls for users that may not exist in Clerk.
    if include_image_urls:
        image_url_tasks = [
            get_clerk_user_image_url(user_id=user_dict["user_id"])
            for user_dict in users_with_project_ids
        ]
        image_urls = await asyncio.gather(*image_url_tasks)
        for user_dict, image_url in zip(users_with_project_ids, image_urls):
            if image_url:
                user_dict["image_url"] = image_url

    return users_with_project_ids


@router.get(
    "/self",
    response_model=interfaces.UserData,
)
async def get_self(
    user_data: Annotated[dict, Depends(dependencies.get_user_data_async)],
):
    """Return the authenticated user's session data.

    Args:
        user_data: Context data injected from the authentication middleware.
    """
    return user_data


@router.post(
    "/create-with-clerk",
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def create_user(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: UserCreate,
):
    """Create a user in Clerk and persist metadata in the admin database.

    Args:
        db: Async session for admin persistence actions.
        user: UserCreate payload containing Clerk and company details.
    """
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
    """todo

    Args:
        db: TODO: describe.
        user_id: TODO: describe.
    """
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
    """Update the current user's theme in Clerk.

    Args:
        user_data: TODO: describe.
        request: TODO: describe.
    """
    user_id = user_data.user_id
    return await update_clerk_user_theme(
        user_id=user_id,
        theme=request.theme,
        vite_environment=request.vite_environment,
    )


@router.put(
    "/self/clerk-demo-mode",
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def update_self_clerk_demo_mode(
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
    request: DemoModeUpdateRequest,
):
    """Update the current user's demo mode in Clerk.

    Args:
        user_data: TODO: describe.
        request: TODO: describe.
    """
    user_id = user_data.user_id
    return await update_clerk_user_demo_mode(
        user_id=user_id,
        demo_mode=request.demo_mode,
        vite_environment=request.vite_environment,
    )
