from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models
from core.db_query import DbQuery


def get_recent_notification(
    *,
    project_id: Any,
    notification_type_id: int,
) -> DbQuery[models.Notification, Literal[True]]:
    """Get the most recent notification for a project and type.

    Args:
        project_id: Project identifier.
        notification_type_id: Notification type identifier.

    Returns:
        DbQuery for most recent notification.
    """
    stmt = (
        select(models.Notification)
        .where(
            models.Notification.project_id == project_id,
            models.Notification.notification_type_id == notification_type_id,
        )
        .order_by(models.Notification.created_at.desc())
        .limit(1)
    )
    return DbQuery(query=stmt, is_scalar=True)


def get_notification_preferences_for_project(
    *,
    project_id: Any,
    notification_type_id: int,
) -> DbQuery[models.NotificationPreference, Literal[False]]:
    """Get notification preferences for a project and type.

    Args:
        project_id: Project identifier.
        notification_type_id: Notification type identifier.

    Returns:
        DbQuery for notification preferences.
    """
    stmt = select(models.NotificationPreference).where(
        models.NotificationPreference.project_id == project_id,
        models.NotificationPreference.notification_type_id == notification_type_id,
    )
    return DbQuery(query=stmt)


async def create_notification(
    *,
    db: AsyncSession,
    project_id: Any,
    notification_type_id: int,
    data: dict,
    severity: enumerations.NotificationSeverity,
) -> models.Notification:
    """Create a new notification.

    Args:
        db: Database session.
        project_id: Project identifier.
        notification_type_id: Notification type identifier.
        data: Notification data payload.
        severity: Notification severity level.

    Returns:
        Created notification model.
    """
    notification = models.Notification(
        project_id=project_id,
        notification_type_id=notification_type_id,
        data=data,
        severity=severity,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def create_notification_state(
    *,
    db: AsyncSession,
    notification_id: int,
    user_id: str,
    channel: enumerations.NotificationChannel,
    state: enumerations.NotificationState = enumerations.NotificationState.UNREAD,
) -> models.NotificationState:
    """Create a notification state for a user.

    Args:
        db: Database session.
        notification_id: Notification identifier.
        user_id: User identifier.
        channel: Notification channel (email/in_app).
        state: Notification state (unread/read/deleted).

    Returns:
        Created notification state model.
    """
    notification_state = models.NotificationState(
        notification_id=notification_id,
        user_id=user_id,
        channel=channel,
        state=state,
    )
    db.add(notification_state)
    await db.commit()
    await db.refresh(notification_state)
    return notification_state
