from typing import Annotated

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

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=list[interfaces.Notification],
    description="Get all IN_APP notifications for the requesting user.",
)
async def get_user_notifications(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Get all IN_APP notifications for the requesting user.

    Args:
        db: Database session.
        user_data: Authenticated user data.
        limit: Optional max number of notifications to return.
        offset: Number of notifications to skip before returning results.

    Returns:
        List of Notification objects with IN_APP channel that are not deleted,
        including state. Pagination is supported via limit/offset.
    """
    notification_tuples = await crud_get_user_in_app_notifications(
        db=db,
        user_id=user_data.user_id,
        limit=limit,
        offset=offset,
    )
    # Convert tuples to Notification objects with state
    notifications: list[interfaces.Notification] = []
    for notification, notification_state in notification_tuples:
        notifications.append(
            interfaces.Notification(
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
async def get_unread_notification_count(
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    """Return the unread IN_APP notification count for the requesting user.

    Args:
        user_data: Authenticated user data.

    Returns:
        Dictionary with count of unread notifications.
    """
    count = await crud_get_unread_notification_count(
        user_id=user_data.user_id
    ).get_async(output_type=OutputType.SQLALCHEMY)
    return {"count": count}


@router.delete(
    "/delete-all",
    status_code=204,
    description="Delete all IN_APP notifications for the requesting user.",
)
async def delete_all_notifications(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    """Mark all IN_APP notifications as deleted for the requesting user.

    Args:
        db: Database session.
        user_data: Authenticated user data.
    """
    await crud_delete_all_notifications(db=db, user_id=user_data.user_id)


@router.put(
    "/{notification_id}/read",
    response_model=interfaces.Notification,
    description="Mark a notification as read for the requesting user.",
)
async def mark_notification_read(
    notification_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
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
    )
    for notification, ns in notification_tuples:
        if notification.notification_id == notification_id:
            return interfaces.Notification(
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
    response_model=interfaces.Notification,
    description="Mark a notification as unread for the requesting user.",
)
async def mark_notification_unread(
    notification_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
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
    )
    for notification, ns in notification_tuples:
        if notification.notification_id == notification_id:
            return interfaces.Notification(
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
async def delete_notification(
    notification_id: Annotated[int, Path(...)],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
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
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    """Mark all IN_APP notifications as read for the requesting user.

    Args:
        db: Database session.
        user_data: Authenticated user data.

    Returns:
        Dictionary with count of notifications marked as read.
    """
    count = await crud_mark_all_notifications_as_read(
        db=db,
        user_id=user_data.user_id,
    )

    return {"count": count}
