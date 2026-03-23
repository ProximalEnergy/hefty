from typing import Any, Literal
from uuid import UUID

from sqlalchemy import false, func, select, update
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


def get_most_recent_notifications(
    *,
    project_ids: list[UUID] | None = None,
    notification_type_ids: list[int] | None = None,
    is_active: bool | None = None,
) -> DbQuery[models.Notification, Literal[False]]:
    """Latest notification per (project, type) among rows matching the filters.

    Uses ``row_number()`` over ``(project_id, notification_type_id)`` ordered by
    ``created_at`` descending, then keeps ``rn == 1``.

    Args:
        project_ids: If set, restrict to these projects. An empty list matches
            nothing.
        notification_type_ids: If set, restrict to these types. An empty list
            matches nothing.
        is_active: If set, restrict to this ``is_active`` value.

    Returns:
        DbQuery for zero or more :class:`~core.models.Notification` rows.
    """
    n = models.Notification
    filters: list = []
    if project_ids is not None:
        if not project_ids:
            stmt = select(n).where(false())
            return DbQuery(query=stmt, is_scalar=False)
        filters.append(n.project_id.in_(project_ids))
    if notification_type_ids is not None:
        if not notification_type_ids:
            stmt = select(n).where(false())
            return DbQuery(query=stmt, is_scalar=False)
        filters.append(n.notification_type_id.in_(notification_type_ids))
    if is_active is not None:
        filters.append(n.is_active == is_active)

    ranked_select = select(
        n.notification_id,
        func.row_number()
        .over(
            partition_by=(n.project_id, n.notification_type_id),
            order_by=n.created_at.desc(),
        )
        .label("rn"),
    ).select_from(n)
    if filters:
        ranked_select = ranked_select.where(*filters)
    ranked_subq = ranked_select.subquery()

    stmt = (
        select(n)
        .join(ranked_subq, n.notification_id == ranked_subq.c.notification_id)
        .where(ranked_subq.c.rn == 1)
    )
    return DbQuery(query=stmt, is_scalar=False)


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


def update_notifications_is_active(
    *,
    notification_ids: list[int],
    is_active: bool,
) -> DbQuery[Any, Literal[False]]:
    """Build an UPDATE that sets is_active for a notification.

    Run with ``execute_async()`` or ``execute()`` on the returned DbQuery.
    Pass ``schema`` through to match other admin DbQuery usage if needed.

    Args:
        notification_id: Notification identifier.
        is_active: New value for is_active.

    Returns:
        DbQuery wrapping the UPDATE statement.
    """
    stmt = (
        update(models.Notification)
        .where(models.Notification.notification_id.in_(notification_ids))
        .values(is_active=is_active)
    )
    return DbQuery(query=stmt)
