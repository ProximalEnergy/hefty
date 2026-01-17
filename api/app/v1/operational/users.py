import asyncio
from typing import Annotated

from core.crud.admin.users import get_users as get_users_core
from core.db_query import OutputType
from fastapi import APIRouter, Depends, Query

from app import dependencies
from app._dependencies.authorization import require_jwt_or_api_superadmin
from app._utils.user_management import get_clerk_user_image_url

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_jwt_or_api_superadmin)],
)


@router.get("")
async def get_users(
    user_data: Annotated[
        dependencies.interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
    user_ids: list[str] | None = Query(
        default=None, description="Filter by specific user IDs"
    ),
    include_image_urls: bool = Query(
        default=False, description="Include user profile image URLs from Clerk"
    ),
):
    # If user_ids is provided, fetch those specific users
    # Otherwise, fetch all users from the same company
    """todo

    Args:
        user_data: TODO: describe.
        user_ids: TODO: describe.
        include_image_urls: TODO: describe.
    """
    if user_ids:
        # Fetch requested users - security is handled at the message/project level:
        # user_ids come from event messages in projects the user has access to,
        # so it's safe to return user information for these IDs
        filtered_users = await get_users_core(user_ids=user_ids).get_async(
            output_type=OutputType.SQLALCHEMY
        )
    else:
        filtered_users = await get_users_core(
            company_ids=[user_data.company_id]
        ).get_async(output_type=OutputType.SQLALCHEMY)

    # Process each user tuple and add operational_project_ids and optionally image URLs
    users_with_project_ids = []
    for user in filtered_users:
        user_dict = {
            **{k: v for k, v in user[0].__dict__.items() if k != "api_key"},
            "operational_project_ids": user[1],
        }
        users_with_project_ids.append(user_dict)

    # Fetch image URLs in parallel if requested
    if include_image_urls:
        image_url_tasks = [
            get_clerk_user_image_url(user_id=user[0].user_id) for user in filtered_users
        ]
        image_urls = await asyncio.gather(*image_url_tasks)
        for user_dict, image_url in zip(users_with_project_ids, image_urls):
            if image_url:
                user_dict["image_url"] = image_url

    return users_with_project_ids
