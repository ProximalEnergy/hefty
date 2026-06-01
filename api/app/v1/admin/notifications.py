from typing import Annotated
from uuid import UUID

from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.notifications import (
    delete_all_notifications as crud_delete_all_notifications,
)
from app._crud.admin.notifications import (
    delete_notification as crud_delete_notification,
)
from app._crud.admin.notifications import (
    get_unread_notification_count as crud_get_unread_notification_count,
)
from app._crud.admin.notifications import (
    get_user_in_app_notifications as crud_get_user_in_app_notifications,
)
from app._crud.admin.notifications import (
    mark_all_notifications_as_read as crud_mark_all_notifications_as_read,
)
from app._crud.admin.notifications import (
    mark_notification_as_read as crud_mark_notification_as_read,
)
from app._crud.admin.notifications import (
    mark_notification_as_unread as crud_mark_notification_as_unread,
)
from app._dependencies.authentication import get_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_personal_portfolio_project_ids(
    *,
    permitted_project_ids: list[UUID],
    project_ids_excluded: list[UUID] | None,
) -> list[UUID]:
    """Return projects currently enabled in the user's Personal Portfolio.

    Args:
        permitted_project_ids: Project IDs the user can access.
        project_ids_excluded: Project IDs hidden from the user's Personal
            Portfolio.
    """
    if not project_ids_excluded:
        return permitted_project_ids

    return list(set(permitted_project_ids) - set(project_ids_excluded))


@router.get(
    "",
    response_model=list[interfaces.NotificationInterface],
    description="Get all IN_APP notifications for the requesting user.",
)
async def get_user_notifications(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
    project_ids_excluded: Annotated[list[UUID] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Get all IN_APP notifications for the requesting user.

    Args:
        db: Database session.
        user_data: Authenticated user data.
        project_ids_excluded: Project IDs hidden from the user's Personal
            Portfolio.
        limit: Optional max number of notifications to return.
        offset: Number of notifications to skip before returning results.

    Returns:
        List of Notification objects with IN_APP channel that are not deleted,
        including state. Pagination is supported via limit/offset.
    """
    project_ids_enabled = get_personal_portfolio_project_ids(
        permitted_project_ids=user_data.operational_project_ids,
        project_ids_excluded=project_ids_excluded,
    )
    notification_tuples = await crud_get_user_in_app_notifications(
        db=db,
        user_id=user_data.user_id,
        project_ids_included=project_ids_enabled,
        limit=limit,
        offset=offset,
    )
    # Convert tuples to Notification objects with state
    notifications: list[interfaces.NotificationInterface] = []
    for notification, notification_state in notification_tuples:
        notifications.append(
            interfaces.NotificationInterface(
                notification_id=notification.notification_id,
                project_id=notification.project_id,
                notification_type_id=notification.notification_type_id,
                data=notification.data,
                severity=notification.severity.value,
                created_at=notification.created_at,
                sent_at=notification.sent_at,
                state=notification_state.state.value,
            )
        )
    return notifications


@router.get(
    "/unread-count",
    response_model=dict[str, int],
    description="Get count of unread IN_APP notifications for the requesting user.",
)
async def get_unread_notification_count_route(
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
    project_ids_excluded: Annotated[list[UUID] | None, Query()] = None,
):
    """Return the unread IN_APP notification count for the requesting user.

    Args:
        user_data: Authenticated user data.
        project_ids_excluded: Project IDs hidden from the user's Personal
            Portfolio.

    Returns:
        Dictionary with count of unread notifications.
    """
    project_ids_enabled = get_personal_portfolio_project_ids(
        permitted_project_ids=user_data.operational_project_ids,
        project_ids_excluded=project_ids_excluded,
    )
    count = await crud_get_unread_notification_count(
        user_id=user_data.user_id,
        project_ids_included=project_ids_enabled,
    ).get_async(output_type=OutputType.SQLALCHEMY)
    return {"count": count}


@router.delete(
    "/delete-all",
    status_code=204,
    description="Delete all IN_APP notifications for the requesting user.",
)
async def delete_all_notifications_route(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
    project_ids_excluded: Annotated[list[UUID] | None, Query()] = None,
):
    """Mark all IN_APP notifications as deleted for the requesting user.

    Args:
        db: Database session.
        user_data: Authenticated user data.
        project_ids_excluded: Project IDs hidden from the user's Personal
            Portfolio.
    """
    project_ids_enabled = get_personal_portfolio_project_ids(
        permitted_project_ids=user_data.operational_project_ids,
        project_ids_excluded=project_ids_excluded,
    )
    await crud_delete_all_notifications(
        db=db,
        user_id=user_data.user_id,
        project_ids_included=project_ids_enabled,
    )


@router.put(
    "/{notification_id}/read",
    response_model=interfaces.NotificationInterface,
    description="Mark a notification as read for the requesting user.",
)
async def mark_notification_read(
    notification_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    """Mark a notification as read for the requesting user.

    Args:
        notification_id: Notification ID to mark as read.
        db: Database session.
        user_data: Authenticated user data.

    Returns:
        Updated Notification object with state set to "read".

    Raises:
        HTTPException: 404 if notification not found or not accessible to user.
    """
    notification_state = await crud_mark_notification_as_read(
        db=db,
        notification_id=notification_id,
        user_id=user_data.user_id,
    )

    if not notification_state:
        raise HTTPException(
            status_code=404,
            detail="Notification not found or not accessible",
        )

    # Get the updated notification with state
    notification_tuples = await crud_get_user_in_app_notifications(
        db=db,
        user_id=user_data.user_id,
        project_ids_included=user_data.operational_project_ids,
    )
    for notification, ns in notification_tuples:
        if notification.notification_id == notification_id:
            return interfaces.NotificationInterface(
                notification_id=notification.notification_id,
                project_id=notification.project_id,
                notification_type_id=notification.notification_type_id,
                data=notification.data,
                severity=notification.severity.value,
                created_at=notification.created_at,
                sent_at=notification.sent_at,
                state=ns.state.value,
            )

    raise HTTPException(
        status_code=404,
        detail="Notification not found after update",
    )


@router.put(
    "/{notification_id}/unread",
    response_model=interfaces.NotificationInterface,
    description="Mark a notification as unread for the requesting user.",
)
async def mark_notification_unread(
    notification_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    """Mark a notification as unread for the requesting user.

    Args:
        notification_id: Notification ID to mark as unread.
        db: Database session.
        user_data: Authenticated user data.

    Returns:
        Updated Notification object with state set to "unread".

    Raises:
        HTTPException: 404 if notification not found or not accessible to user.
    """
    notification_state = await crud_mark_notification_as_unread(
        db=db,
        notification_id=notification_id,
        user_id=user_data.user_id,
    )

    if not notification_state:
        raise HTTPException(
            status_code=404,
            detail="Notification not found or not accessible",
        )

    # Get the updated notification with state
    notification_tuples = await crud_get_user_in_app_notifications(
        db=db,
        user_id=user_data.user_id,
        project_ids_included=user_data.operational_project_ids,
    )
    for notification, ns in notification_tuples:
        if notification.notification_id == notification_id:
            return interfaces.NotificationInterface(
                notification_id=notification.notification_id,
                project_id=notification.project_id,
                notification_type_id=notification.notification_type_id,
                data=notification.data,
                severity=notification.severity.value,
                created_at=notification.created_at,
                sent_at=notification.sent_at,
                state=ns.state.value,
            )

    raise HTTPException(
        status_code=404,
        detail="Notification not found after update",
    )


@router.delete(
    "/{notification_id}",
    status_code=204,
    description="Delete a notification for the requesting user.",
)
async def delete_notification_route(
    notification_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
):
    """Delete a notification for the requesting user (mark as deleted).

    Args:
        notification_id: Notification ID to delete.
        db: Database session.
        user_data: Authenticated user data.

    Raises:
        HTTPException: 404 if notification not found or not accessible to user.
    """
    notification_state = await crud_delete_notification(
        db=db,
        notification_id=notification_id,
        user_id=user_data.user_id,
    )

    if not notification_state:
        raise HTTPException(
            status_code=404,
            detail="Notification not found or not accessible",
        )

    return None


@router.put(
    "/read-all",
    response_model=dict,
    description="Mark all IN_APP notifications as read for the requesting user.",
)
async def mark_all_notifications_read(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
    project_ids_excluded: Annotated[list[UUID] | None, Query()] = None,
):
    """Mark all IN_APP notifications as read for the requesting user.

    Args:
        db: Database session.
        user_data: Authenticated user data.
        project_ids_excluded: Project IDs hidden from the user's Personal
            Portfolio.

    Returns:
        Dictionary with count of notifications marked as read.
    """
    project_ids_enabled = get_personal_portfolio_project_ids(
        permitted_project_ids=user_data.operational_project_ids,
        project_ids_excluded=project_ids_excluded,
    )
    count = await crud_mark_all_notifications_as_read(
        db=db,
        user_id=user_data.user_id,
        project_ids_included=project_ids_enabled,
    )

    return {"count": count}
