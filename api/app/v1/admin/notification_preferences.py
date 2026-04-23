from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces, utils
from app._crud.admin.notification_preferences import (
    get_user_notification_preferences as crud_get_user_notification_preferences,
)
from app._crud.admin.notification_preferences import (
    update_notification_preference as crud_update_notification_preference,
)
from app._dependencies.authentication import get_user

router = APIRouter(
    prefix="/notification-preferences",
    tags=["notification-preferences"],
    include_in_schema=utils.get_include_in_schema(),
)


@router.get(
    "",
    response_model=list[interfaces.NotificationPreference],
    description="Get notification preferences for the requesting user.",
)
async def get_user_notification_preferences(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
    project_ids: list[UUID] | None = Query(None, description="Filter by project IDs"),
):
    """Get notification preferences for the requesting user.

    Args:
        db: Database session.
        user_data: User data.
        project_ids: Optional list of project IDs to filter by.
    """
    try:
        preferences = await crud_get_user_notification_preferences(
            db=db,
            user_id=user_data.user_id,
            project_ids=project_ids,
        )
        return preferences
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get notification preferences: {str(e)}",
        )


@router.put(
    "",
    response_model=interfaces.NotificationPreference,
    description="Update a notification preference.",
)
async def update_notification_preference(
    data: interfaces.NotificationPreferenceUpdate,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    """Update a notification preference.

    Args:
        data: Update data including project_id and notification_type_id.
        db: Database session.
        user_data: User data.
    """
    if data.project_id not in user_data.operational_project_ids:
        raise HTTPException(
            status_code=403,
            detail="User does not have access to this project",
        )

    try:
        preference = await crud_update_notification_preference(
            db=db,
            user_id=user_data.user_id,
            project_id=data.project_id,
            notification_type_id=data.notification_type_id,
            in_app_enabled=data.in_app_enabled,
            email_enabled=data.email_enabled,
            in_app_min_severity=data.in_app_min_severity,
            email_min_severity=data.email_min_severity,
        )
        return preference
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update notification preference: {str(e)}",
        )
