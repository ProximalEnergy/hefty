from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models


async def get_user_in_app_notifications(
    *,
    db: AsyncSession,
    user_id: str,
    limit: int | None = None,
    offset: int = 0,
) -> list[tuple[models.Notification, models.NotificationState]]:
    """Get all IN_APP notifications for a user with their state.

    Args:
        db: Database session.
        user_id: User ID to get notifications for.
        limit: Optional max number of notifications to return.
        offset: Number of notifications to skip before returning results.

    Returns:
        List of tuples containing (Notification, NotificationState) for IN_APP channel that are not deleted.
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
            models.NotificationState.channel == enumerations.NotificationChannel.IN_APP,
            models.NotificationState.state != enumerations.NotificationState.DELETED,
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
        models.NotificationState.channel == enumerations.NotificationChannel.IN_APP,
    )
    result = await db.execute(query)
    notification_state = result.scalar_one_or_none()

    if notification_state:
        notification_state.state = enumerations.NotificationState.READ
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
        models.NotificationState.channel == enumerations.NotificationChannel.IN_APP,
    )
    result = await db.execute(query)
    notification_state = result.scalar_one_or_none()

    if notification_state:
        notification_state.state = enumerations.NotificationState.UNREAD
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
        models.NotificationState.channel == enumerations.NotificationChannel.IN_APP,
    )
    result = await db.execute(query)
    notification_state = result.scalar_one_or_none()

    if notification_state:
        notification_state.state = enumerations.NotificationState.DELETED
        await db.commit()
        await db.refresh(notification_state)
        return notification_state

    return None


async def delete_all_notifications(
    *,
    db: AsyncSession,
    user_id: str,
) -> int:
    """Mark all IN_APP notifications as deleted for a user.

    Args:
        db: Database session.
        user_id: User ID.

    Returns:
        Number of notifications marked as deleted.
    """
    query = select(models.NotificationState).where(
        models.NotificationState.user_id == user_id,
        models.NotificationState.channel == enumerations.NotificationChannel.IN_APP,
        models.NotificationState.state != enumerations.NotificationState.DELETED,
    )
    result = await db.execute(query)
    notification_states = result.scalars().all()

    count = 0
    for notification_state in notification_states:
        notification_state.state = enumerations.NotificationState.DELETED
        count += 1

    if count > 0:
        await db.commit()

    return count


async def mark_all_notifications_as_read(
    *,
    db: AsyncSession,
    user_id: str,
) -> int:
    """Mark all IN_APP notifications as read for a user.

    Args:
        db: Database session.
        user_id: User ID.

    Returns:
        Number of notifications marked as read.
    """
    query = select(models.NotificationState).where(
        models.NotificationState.user_id == user_id,
        models.NotificationState.channel == enumerations.NotificationChannel.IN_APP,
        models.NotificationState.state == enumerations.NotificationState.UNREAD,
    )
    result = await db.execute(query)
    notification_states = result.scalars().all()

    count = 0
    for notification_state in notification_states:
        notification_state.state = enumerations.NotificationState.READ
        count += 1

    if count > 0:
        await db.commit()

    return count


async def get_unread_notification_count(
    *,
    db: AsyncSession,
    user_id: str,
) -> int:
    """Get the count of unread IN_APP notifications for a user.

    This is a lightweight query that only counts, doesn't fetch full notification data.

    Args:
        db: Database session.
        user_id: User ID to get unread count for.

    Returns:
        Count of unread IN_APP notifications.
    """
    query = select(func.count(models.NotificationState.notification_state_id)).where(
        models.NotificationState.user_id == user_id,
        models.NotificationState.channel == enumerations.NotificationChannel.IN_APP,
        models.NotificationState.state == enumerations.NotificationState.UNREAD,
    )
    result = await db.execute(query)
    return result.scalar_one() or 0
