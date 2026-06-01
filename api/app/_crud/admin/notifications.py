from typing import Literal
from uuid import UUID

from core.db_query import DbQuery
from sqlalchemy import false, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models


async def get_user_in_app_notifications(
    *,
    db: AsyncSession,
    user_id: str,
    project_ids_included: list[UUID],
    limit: int | None = None,
    offset: int = 0,
) -> list[tuple[models.Notification, models.NotificationState]]:
    """Get all IN_APP notifications for a user with their state.

    Args:
        db: Database session.
        user_id: User ID to get notifications for.
        project_ids_included: Project IDs enabled in the user's Personal
            Portfolio.
        limit: Optional max number of notifications to return.
        offset: Number of notifications to skip before returning results.

    Returns:
        List of tuples containing (Notification, NotificationState) for IN_APP
        channel that are not deleted.
    """
    query = (
        select(models.Notification, models.NotificationState)
        .join(
            models.NotificationState,
            models.Notification.notification_id
            == models.NotificationState.notification_id,
        )
        .where(
            models.NotificationState.user_id == user_id,
            models.NotificationState.channel
            == enumerations.NotificationChannelEnum.IN_APP,
            models.NotificationState.state
            != enumerations.NotificationStateEnum.DELETED,
            (
                models.Notification.project_id.in_(project_ids_included)
                if project_ids_included
                else false()
            ),
        )
        .order_by(models.Notification.created_at.desc())
    )
    if limit is not None:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)
    result = await db.execute(query)
    rows = result.all()
    return [
        (notification, notification_state) for notification, notification_state in rows
    ]


async def mark_notification_as_read(
    *,
    db: AsyncSession,
    notification_id: int,
    user_id: str,
) -> models.NotificationState | None:
    """Mark a notification as read for a user.

    Args:
        db: Database session.
        notification_id: Notification ID to mark as read.
        user_id: User ID.

    Returns:
        Updated NotificationState object, or None if not found.
    """
    query = select(models.NotificationState).where(
        models.NotificationState.notification_id == notification_id,
        models.NotificationState.user_id == user_id,
        models.NotificationState.channel == enumerations.NotificationChannelEnum.IN_APP,
    )
    result = await db.execute(query)
    notification_state = result.scalar_one_or_none()

    if notification_state:
        notification_state.state = enumerations.NotificationStateEnum.READ
        await db.commit()
        await db.refresh(notification_state)
        return notification_state

    return None


async def mark_notification_as_unread(
    *,
    db: AsyncSession,
    notification_id: int,
    user_id: str,
) -> models.NotificationState | None:
    """Mark a notification as unread for a user.

    Args:
        db: Database session.
        notification_id: Notification ID to mark as unread.
        user_id: User ID.

    Returns:
        Updated NotificationState object, or None if not found.
    """
    query = select(models.NotificationState).where(
        models.NotificationState.notification_id == notification_id,
        models.NotificationState.user_id == user_id,
        models.NotificationState.channel == enumerations.NotificationChannelEnum.IN_APP,
    )
    result = await db.execute(query)
    notification_state = result.scalar_one_or_none()

    if notification_state:
        notification_state.state = enumerations.NotificationStateEnum.UNREAD
        await db.commit()
        await db.refresh(notification_state)
        return notification_state

    return None


async def delete_notification(
    *,
    db: AsyncSession,
    notification_id: int,
    user_id: str,
) -> models.NotificationState | None:
    """Delete a notification for a user (mark as deleted).

    Args:
        db: Database session.
        notification_id: Notification ID to delete.
        user_id: User ID.

    Returns:
        Updated NotificationState object, or None if not found.
    """
    query = select(models.NotificationState).where(
        models.NotificationState.notification_id == notification_id,
        models.NotificationState.user_id == user_id,
        models.NotificationState.channel == enumerations.NotificationChannelEnum.IN_APP,
    )
    result = await db.execute(query)
    notification_state = result.scalar_one_or_none()

    if notification_state:
        notification_state.state = enumerations.NotificationStateEnum.DELETED
        await db.commit()
        await db.refresh(notification_state)
        return notification_state

    return None


async def delete_all_notifications(
    *,
    db: AsyncSession,
    user_id: str,
    project_ids_included: list[UUID],
) -> int:
    """Mark all IN_APP notifications as deleted for a user.

    Args:
        db: Database session.
        user_id: User ID.
        project_ids_included: Project IDs enabled in the user's Personal
            Portfolio.

    Returns:
        Number of notifications marked as deleted.
    """
    query = (
        select(models.NotificationState)
        .join(
            models.Notification,
            models.Notification.notification_id
            == models.NotificationState.notification_id,
        )
        .where(
            models.NotificationState.user_id == user_id,
            models.NotificationState.channel
            == enumerations.NotificationChannelEnum.IN_APP,
            models.NotificationState.state
            != enumerations.NotificationStateEnum.DELETED,
            (
                models.Notification.project_id.in_(project_ids_included)
                if project_ids_included
                else false()
            ),
        )
    )
    result = await db.execute(query)
    notification_states = result.scalars().all()

    count = 0
    for notification_state in notification_states:
        notification_state.state = enumerations.NotificationStateEnum.DELETED
        count += 1

    if count > 0:
        await db.commit()

    return count


async def mark_all_notifications_as_read(
    *,
    db: AsyncSession,
    user_id: str,
    project_ids_included: list[UUID],
) -> int:
    """Mark all IN_APP notifications as read for a user.

    Args:
        db: Database session.
        user_id: User ID.
        project_ids_included: Project IDs enabled in the user's Personal
            Portfolio.

    Returns:
        Number of notifications marked as read.
    """
    query = (
        select(models.NotificationState)
        .join(
            models.Notification,
            models.Notification.notification_id
            == models.NotificationState.notification_id,
        )
        .where(
            models.NotificationState.user_id == user_id,
            models.NotificationState.channel
            == enumerations.NotificationChannelEnum.IN_APP,
            models.NotificationState.state == enumerations.NotificationStateEnum.UNREAD,
            (
                models.Notification.project_id.in_(project_ids_included)
                if project_ids_included
                else false()
            ),
        )
    )
    result = await db.execute(query)
    notification_states = result.scalars().all()

    count = 0
    for notification_state in notification_states:
        notification_state.state = enumerations.NotificationStateEnum.READ
        count += 1

    if count > 0:
        await db.commit()

    return count


def get_unread_notification_count(
    *,
    user_id: str,
    project_ids_included: list[UUID],
) -> DbQuery[int, Literal[True]]:
    """Get the count of unread IN_APP notifications for a user.

    This is a lightweight query that only counts, doesn't fetch full notification data.

    Args:
        user_id: User ID to get unread count for.
        project_ids_included: Project IDs enabled in the user's Personal
            Portfolio.

    Returns:
        Count of unread IN_APP notifications.
    """
    query = (
        select(func.count(models.NotificationState.notification_state_id))
        .join(
            models.Notification,
            models.Notification.notification_id
            == models.NotificationState.notification_id,
        )
        .where(
            models.NotificationState.user_id == user_id,
            models.NotificationState.channel
            == enumerations.NotificationChannelEnum.IN_APP,
            models.NotificationState.state == enumerations.NotificationStateEnum.UNREAD,
            (
                models.Notification.project_id.in_(project_ids_included)
                if project_ids_included
                else false()
            ),
        )
    )
    return DbQuery(query=query, is_scalar=True)
