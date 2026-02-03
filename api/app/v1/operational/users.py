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
            output_type=OutputType.PANDAS
        )
    else:
        filtered_users = await get_users_core(
            company_ids=[user_data.company_id]
        ).get_async(output_type=OutputType.PANDAS)

    project_ids_by_user = (
        filtered_users.dropna(subset=["project_ids"])
        .groupby("user_id")["project_ids"]
        .unique()
        .apply(list)
    )
    base_users = filtered_users.drop(columns=["project_ids"]).drop_duplicates("user_id")
    if "api_key" in base_users.columns:
        base_users = base_users.drop(columns=["api_key"])
    base_users["operational_project_ids"] = base_users["user_id"].map(
        project_ids_by_user
    )
    base_users["operational_project_ids"] = base_users["operational_project_ids"].apply(
        lambda value: value if isinstance(value, list) else []
    )

    users_with_project_ids = base_users.to_dict(orient="records")

    # Fetch image URLs in parallel if requested
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
