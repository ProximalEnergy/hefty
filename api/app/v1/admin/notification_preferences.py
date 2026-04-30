from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces, utils
from app._crud.admin.notification_preferences import (
    bulk_update_notification_preferences as crud_bulk_update_notification_preferences,
)
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
    "/bulk",
    response_model=list[interfaces.NotificationPreference],
    description="Update multiple notification preferences.",
)
async def bulk_update_notification_preferences(
    data: interfaces.NotificationPreferenceBulkUpdate,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    """Update multiple notification preferences.

    Args:
        data: Bulk update data including projects and notification types.
        db: Database session.
        user_data: User data.
    """
    has_update = any(
        value is not None
        for value in [
            data.in_app_enabled,
            data.email_enabled,
            data.in_app_min_severity,
            data.email_min_severity,
        ]
    )
    if not has_update:
        raise HTTPException(
            status_code=400,
            detail="At least one notification preference field is required",
        )

    permitted_project_ids = set(user_data.operational_project_ids)
    denied_project_ids = [
        project_id
        for project_id in data.project_ids
        if project_id not in permitted_project_ids
    ]
    if denied_project_ids:
        raise HTTPException(
            status_code=403,
            detail="User does not have access to all requested projects",
        )

    try:
        preferences = await crud_bulk_update_notification_preferences(
            db=db,
            user_id=user_data.user_id,
            project_ids=data.project_ids,
            notification_type_ids=data.notification_type_ids,
            in_app_enabled=data.in_app_enabled,
            email_enabled=data.email_enabled,
            in_app_min_severity=data.in_app_min_severity,
            email_min_severity=data.email_min_severity,
        )
        return preferences
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update notification preferences: {str(e)}",
        )


@router.put(
    "",
    response_model=interfaces.NotificationPreference,
    description="Update a notification preference.",
    operation_id="update_notification_preference",
)
async def update_notification_preference_route(
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
