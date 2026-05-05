import typing
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import (
    case,
    cast,
    exists,
    false,
    func,
    literal,
    select,
    union_all,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.schema import Table

from core import enumerations, models
from core.db_query import DbQuery


def _notification_severity_rank_expr(
    *,
    severity_col: Any,
) -> Any:
    """Numeric rank for ``admin.notification_severity`` (matches severity_to_numeric).

    Args:
        severity_col: SQLAlchemy column or expression typed as notification severity.

    Returns:
        CASE expression yielding 1 (info), 2 (warning), or 3 (critical).
    """
    info = enumerations.NotificationSeverity.INFO
    warning = enumerations.NotificationSeverity.WARNING
    critical = enumerations.NotificationSeverity.CRITICAL
    return case(
        (severity_col == info, 1),
        (severity_col == warning, 2),
        (severity_col == critical, 3),
        else_=1,
    )


def _notification_type_default_severity_rank_expr(*, default_severity_col: Any) -> Any:
    """Default threshold rank; NULL default severity means INFO (rank 1).

    Args:
        default_severity_col: SQLAlchemy column or expression for the
            notification type's default severity (may be NULL).
    """
    return case(
        (default_severity_col.is_(None), 1),
        else_=_notification_severity_rank_expr(severity_col=default_severity_col),
    )


def _notification_severity_to_int(
    *,
    severity: enumerations.NotificationSeverity,
) -> int:
    """Python-side severity rank (must match ``_notification_severity_rank_expr``).

    Args:
        severity: Notification severity enum value to convert.
    """
    return {
        enumerations.NotificationSeverity.INFO: 1,
        enumerations.NotificationSeverity.WARNING: 2,
        enumerations.NotificationSeverity.CRITICAL: 3,
    }.get(severity, 1)


# Postgres admin.* enum labels (see Alembic). Python StrEnum ``.value`` is lower case
# and does not match what ``CAST(... AS admin.notification_channel)`` accepts.
_PG_NOTIFICATION_CHANNEL_IN_APP = "IN_APP"
_PG_NOTIFICATION_CHANNEL_EMAIL = "EMAIL"
_PG_NOTIFICATION_STATE_UNREAD = "UNREAD"


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
    channel: enumerations.NotificationChannelEnum,
    state: enumerations.NotificationStateEnum = (
        enumerations.NotificationStateEnum.UNREAD
    ),
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


def insert_notification_states_for_recipients(
    *,
    notification_id: int,
    project_id: UUID,
    notification_type_id: int,
    severity: enumerations.NotificationSeverity,
) -> DbQuery[Any, Literal[False]]:
    """Bulk-insert ``notification_states`` for all eligible users and channels.

    Matches recipient rules in
    ``core.utils.notifications.determine_notification_recipients``:
    explicit ``notification_preferences`` per channel and severity threshold, else
    ``notification_types`` defaults (NULL default severities treated as INFO).

    Run with ``execute()`` / ``execute_async()`` on the returned ``DbQuery``. Use
    ``schema=None`` when executing against the admin database if required by your
    session factory. Conflicts on ``(notification_id, user_id, channel)`` are
    ignored (idempotent).

    Args:
        notification_id: Target notification primary key.
        project_id: Operational project UUID (must match the notification row).
        notification_type_id: Notification type id (must match the notification).
        severity: Severity of the notification event.

    Returns:
        ``DbQuery`` wrapping a PostgreSQL ``INSERT ... SELECT ... ON CONFLICT DO
        NOTHING``.
    """
    np = models.NotificationPreference
    nt = models.NotificationType
    up = models.UserProject
    ch = models.notification_channel_enum
    st = models.notification_state_enum
    notif_rank = _notification_severity_to_int(severity=severity)
    in_app_ch = cast(literal(_PG_NOTIFICATION_CHANNEL_IN_APP), ch)
    email_ch = cast(literal(_PG_NOTIFICATION_CHANNEL_EMAIL), ch)
    unread_st = cast(literal(_PG_NOTIFICATION_STATE_UNREAD), st)

    explicit_in_app = select(
        literal(notification_id).label("notification_id"),
        np.user_id.label("user_id"),
        in_app_ch.label("channel"),
        unread_st.label("state"),
    ).where(
        np.project_id == project_id,
        np.notification_type_id == notification_type_id,
        np.in_app_enabled.is_(True),
        literal(notif_rank)
        >= _notification_severity_rank_expr(severity_col=np.in_app_min_severity),
    )
    explicit_email = select(
        literal(notification_id).label("notification_id"),
        np.user_id.label("user_id"),
        email_ch.label("channel"),
        unread_st.label("state"),
    ).where(
        np.project_id == project_id,
        np.notification_type_id == notification_type_id,
        np.email_enabled.is_(True),
        literal(notif_rank)
        >= _notification_severity_rank_expr(severity_col=np.email_min_severity),
    )

    no_preference = ~exists().where(
        np.user_id == up.user_id,
        np.project_id == project_id,
        np.notification_type_id == notification_type_id,
    )

    default_in_app = (
        select(
            literal(notification_id).label("notification_id"),
            up.user_id.label("user_id"),
            in_app_ch.label("channel"),
            unread_st.label("state"),
        )
        .select_from(up)
        .join(nt, nt.notification_type_id == notification_type_id)
        .where(
            up.operational_project_id == project_id,
            no_preference,
            nt.in_app_enabled_default.is_(True),
            literal(notif_rank)
            >= _notification_type_default_severity_rank_expr(
                default_severity_col=nt.in_app_severity_default
            ),
        )
    )
    default_email = (
        select(
            literal(notification_id).label("notification_id"),
            up.user_id.label("user_id"),
            email_ch.label("channel"),
            unread_st.label("state"),
        )
        .select_from(up)
        .join(nt, nt.notification_type_id == notification_type_id)
        .where(
            up.operational_project_id == project_id,
            no_preference,
            nt.email_enabled_default.is_(True),
            literal(notif_rank)
            >= _notification_type_default_severity_rank_expr(
                default_severity_col=nt.email_severity_default
            ),
        )
    )

    combined = union_all(
        explicit_in_app,
        explicit_email,
        default_in_app,
        default_email,
    )
    ns_table = typing.cast(Table, models.NotificationState.__table__)
    stmt = (
        pg_insert(ns_table)
        .from_select(
            [
                ns_table.c.notification_id,
                ns_table.c.user_id,
                ns_table.c.channel,
                ns_table.c.state,
            ],
            combined,
        )
        .on_conflict_do_nothing(
            index_elements=[
                ns_table.c.notification_id,
                ns_table.c.user_id,
                ns_table.c.channel,
            ],
        )
    )
    return DbQuery(query=stmt, is_scalar=False)


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
