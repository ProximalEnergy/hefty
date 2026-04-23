import uuid
from typing import Annotated

import pandas as pd
from core.crud.admin.users import get_users as get_users_core
from core.db_query import OutputType
from core.enumerations import UserTypeEnum
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.users import create_user as create_user_crud
from app._crud.admin.users import delete_user as delete_user_crud
from app._dependencies import authorization
from app._dependencies.authentication import get_user
from app._utils.user_management import (
    create_clerk_user,
    delete_clerk_user,
    get_clerk_user_image_url,
    send_onboarding_email,
    update_clerk_user_demo_mode,
    update_clerk_user_theme,
)
from app.interfaces import User, UserAuthed, UserCreate

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    dependencies=[Depends(authorization.require_jwt_or_api_superadmin)],
    response_model=list[interfaces.UserWithProjects],
)
async def get_users(
    user_data: Annotated[UserAuthed, Depends(get_user)],
    company_ids: list[uuid.UUID] | None = Query(default=None),
    user_ids: list[str] | None = Query(default=None),
    include_image_urls: bool = Query(
        default=False, description="Include user profile image URLs from Clerk"
    ),
):
    """List users along with their operational project assignments.

    Args:
        user_data: Context data injected from the authentication middleware.
        company_ids: Optional list of companies to scope returned users.
        user_ids: Optional list of Clerk user IDs to filter by.
        include_image_urls: Whether to request profile images from Clerk.
    """
    # If the user is not a superadmin, they *have* to request explicit user_ids or users
    # from their own company (company_ids).
    # This is to prevent accidental access to all users or users from other companies.
    if user_data.user_type_id != UserTypeEnum.SUPERADMIN:
        if company_ids != [user_data.company_id] and not user_ids:
            raise HTTPException(
                status_code=403,
                detail=(
                    "You must specify user_ids or company_ids to access this resource",
                ),
            )

    users = await get_users_core(company_ids=company_ids, user_ids=user_ids).get_async(
        output_type=OutputType.PANDAS
    )

    users_with_project_ids = await enrich_users(
        users=users, include_image_urls=include_image_urls
    )

    return users_with_project_ids


@router.get(
    "/self",
    response_model=interfaces.UserAuthed,
)
async def get_self(
    user_data: Annotated[UserAuthed, Depends(get_user)],
):
    """Return the authenticated user's data.

    Args:
        user_data: Context data injected from the authentication middleware.
    """
    return user_data


@router.get(
    "/self-company",
    response_model=list[interfaces.UserWithProjects],
)
async def get_self_company(
    user_data: Annotated[UserAuthed, Depends(get_user)],
):
    """Return all users in the authenticated user's company.

    Args:
        user_data: Context data injected from the authentication middleware.
    """
    users = await get_users_core(company_ids=[user_data.company_id]).get_async(
        output_type=OutputType.PANDAS
    )

    users_with_project_ids = await enrich_users(users=users, include_image_urls=False)

    return users_with_project_ids


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
    """Delete a user from Clerk and the database.

    Args:
        db: Async database session.
        user_id: Clerk user ID to delete.
    """
    await delete_clerk_user(user_id=user_id)
    await delete_user_crud(db=db, user_id=user_id)


class ThemeUpdateRequest(BaseModel):
    """Request body for updating the user's theme preferences in Clerk."""

    theme: str
    vite_environment: str


@router.put(
    "/self/clerk-theme",
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)
async def update_self_clerk_theme(
    user_data: Annotated[UserAuthed, Depends(get_user)],
    request: ThemeUpdateRequest,
):
    """Update the current user's theme in Clerk.

    Args:
        user_data: Authenticated user context.
        request: Theme update payload.
    """
    user_id = user_data.user_id
    return await update_clerk_user_theme(
        user_id=user_id,
        theme=request.theme,
        vite_environment=request.vite_environment,
    )


class DemoModeUpdateRequest(BaseModel):
    """Request body for toggling demo mode flags for a Clerk user."""

    demo_mode: bool
    vite_environment: str


@router.put(
    "/self/clerk-demo-mode",
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def update_self_clerk_demo_mode(
    user_data: Annotated[UserAuthed, Depends(get_user)],
    request: DemoModeUpdateRequest,
):
    """Update the current user's demo mode in Clerk.

    Args:
        user_data: Authenticated user context.
        request: Demo mode update payload.
    """
    user_id = user_data.user_id
    return await update_clerk_user_demo_mode(
        user_id=user_id,
        demo_mode=request.demo_mode,
        vite_environment=request.vite_environment,
    )


async def enrich_users(
    *, users: pd.DataFrame, include_image_urls: bool = False
) -> list:
    """Enrich users with operational project IDs and optionally image URLs.

    Args:
        users: DataFrame of users.
        include_image_urls: Whether to include image URLs from Clerk.

    Returns:
        List of users with operational project IDs and optionally image URLs.
    """
    # Group users by user_id to handle multiple project assignments per user
    if users.empty:
        return []

    users_with_project_ids = []
    for user_id, group in users.groupby("user_id", sort=False):
        # Take the first row to populate user-level metadata
        first_row = group.iloc[0]
        user_dict = {
            **{
                k: v
                for k, v in first_row.to_dict().items()
                if k not in ("api_key", "project_ids")
            },
        }

        # Collect all project IDs from the group, filtering out None/NaN
        # NOTE: This ensures compliance with the UserWithProjects interface.
        project_ids = [
            p
            for p in group["project_ids"].unique().tolist()
            if p is not None and pd.notna(p)
        ]
        user_dict["operational_project_ids"] = project_ids

        # Only fetch profile picture URL from Clerk if explicitly requested
        # This avoids unnecessary API calls for users that may not exist in Clerk
        if include_image_urls:
            image_url = await get_clerk_user_image_url(user_id=str(user_id))
            if image_url:
                user_dict["image_url"] = image_url

        users_with_project_ids.append(user_dict)

    return users_with_project_ids
