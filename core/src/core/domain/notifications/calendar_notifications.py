"""Calendar notification system for calendar item reminders."""

import logging
import os
import traceback
from datetime import UTC, date, datetime, timedelta
from typing import TypedDict
from uuid import UUID

from dateutil.rrule import rrulestr
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models
from core.crud.admin.notifications import (
    create_notification,
    create_notification_state,
)
from core.crud.operational.calendar import (
    get_calendar_item_exceptions,
    get_calendar_items,
)
from core.database import AsyncSessionLambda, async_engine
from core.db_query import OutputType
from core.utils.notifications import (
    determine_notification_recipients,
    ensure_notification_states_exist,
    send_notification_emails_with_rate_limit,
)

logger = logging.getLogger(__name__)

# Setup Jinja2 environment for email templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


class CalendarNotificationsSummary(TypedDict):
    calendar_items_checked: int
    notifications_created: int
    emails_sent: int
    in_app_notifications: int
    errors: list[str]


def parse_offset(*, offset_str: str) -> timedelta:
    """Convert string like '7d' to timedelta(days=7).

    Args:
        offset_str: Offset string like '7d', '1d', '3h', '30m'.

    Returns:
        Timedelta object representing the offset.

    Raises:
        ValueError: If offset format is not supported.
    """
    if offset_str.endswith("d"):
        return timedelta(days=int(offset_str[:-1]))
    elif offset_str.endswith("h"):
        return timedelta(hours=int(offset_str[:-1]))
    elif offset_str.endswith("m"):
        return timedelta(minutes=int(offset_str[:-1]))
    raise ValueError(f"Unsupported offset format: {offset_str}")


async def _get_users_from_assignments(
    *,
    db: AsyncSession,
    calendar_item: models.CalendarItem,
) -> list[str]:
    """Get all user IDs from calendar item assignments (including team members).

    Args:
        db: Database session.
        calendar_item: Calendar item with assignments loaded.

    Returns:
        List of user IDs.
    """
    user_ids: set[str] = set()

    # Get direct user assignments
    for assignment in calendar_item.assignments:
        if assignment.user_id:
            user_ids.add(assignment.user_id)
        elif assignment.team_id:
            # Get team members
            stmt = select(models.TeamMember.user_id).where(
                models.TeamMember.team_id == assignment.team_id
            )
            result = await db.execute(stmt)
            team_user_ids = result.scalars().all()
            user_ids.update(team_user_ids)

    return list(user_ids)


async def check_calendar_notifications(
    *, api_prod: bool = True
) -> CalendarNotificationsSummary:
    """Check calendar items and create notifications for events due today.

    Args:
        api_prod: Whether running in production (affects Clerk API calls).

    Returns:
        Dictionary with summary of notifications created.
    """
    logger.info("Starting calendar notification check function")
    summary: CalendarNotificationsSummary = {
        "calendar_items_checked": 0,
        "notifications_created": 0,
        "emails_sent": 0,
        "in_app_notifications": 0,
        "errors": [],
    }

    async with AsyncSessionLambda() as db:
        try:
            logger.info("Connected to database, fetching calendar items")
            # Get all calendar items with notifications enabled
            calendar_items_query = get_calendar_items(notifications_only=True)
            calendar_items = await calendar_items_query.get_async(
                output_type=OutputType.SQLALCHEMY
            )
            summary["calendar_items_checked"] = len(calendar_items)
            logger.info(
                f"Found {len(calendar_items)} calendar items with notifications"
            )

            if not calendar_items:
                logger.info("No calendar items with notifications found")
                return summary

            # Get all exceptions for these calendar items
            calendar_item_ids = [item.calendar_item_id for item in calendar_items]
            exceptions_query = get_calendar_item_exceptions(
                calendar_item_ids=calendar_item_ids
            )
            exceptions = await exceptions_query.get_async(
                output_type=OutputType.SQLALCHEMY
            )
            # Create a map of calendar_item_id -> list of exception dates
            exceptions_map: dict[UUID, set[date]] = {}
            for exc in exceptions:
                if exc.is_cancelled:
                    if exc.calendar_item_id not in exceptions_map:
                        exceptions_map[exc.calendar_item_id] = set()
                    exceptions_map[exc.calendar_item_id].add(exc.exception_date)

            calendar_notification_type_id = (
                enumerations.NotificationType.CALENDAR_REMINDER.value
            )

            # Ensure current time is UTC-aware
            today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

            # Process each calendar item
            for calendar_item in calendar_items:
                try:
                    await _process_calendar_item(
                        db=db,
                        calendar_item=calendar_item,
                        exceptions_map=exceptions_map,
                        notification_type_id=calendar_notification_type_id,
                        today=today,
                        api_prod=api_prod,
                        summary=summary,
                    )
                except Exception as e:
                    error_msg = (
                        f"Error processing calendar item "
                        f"{calendar_item.calendar_item_id}: {str(e)}"
                    )
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    summary["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Error in check_calendar_notifications: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            summary["errors"].append(error_msg)

    # Ensure notification states exist for all created notifications
    await ensure_notification_states_exist()

    # Ensure the async engine is disposed
    try:
        await async_engine.dispose()
    except Exception as e:
        logger.warning("Error disposing async engine: %s", e)

    return summary


async def _process_calendar_item(
    *,
    db: AsyncSession,
    calendar_item: models.CalendarItem,
    exceptions_map: dict[UUID, set[date]],
    notification_type_id: int,
    today: datetime,
    api_prod: bool,  # noqa: ARG001
    summary: CalendarNotificationsSummary,
) -> None:
    """Process a single calendar item and create notifications if needed.

    Args:
        db: Database session.
        calendar_item: Calendar item to process.
        exceptions_map: Map of calendar_item_id to cancelled exception dates.
        notification_type_id: admin.notification_types id (calendar reminder).
        today: Today's date (UTC, midnight).
        api_prod: Whether running in production.
        summary: Summary dictionary to update.
    """
    if not calendar_item.notify_offsets:
        logger.debug(
            f"Calendar item {calendar_item.calendar_item_id} has no notify_offsets"
        )
        return

    offsets = calendar_item.notify_offsets
    should_notify = False
    occurrence_to_notify: datetime | None = None
    offset_str_to_notify: str | None = None

    # Get cancelled exceptions for this item
    cancelled_dates = exceptions_map.get(calendar_item.calendar_item_id, set())

    if not calendar_item.rrule:
        # Handle non-repeating events
        start_time = calendar_item.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)

        for offset_str in offsets:
            offset = parse_offset(offset_str=offset_str)
            notify_time = start_time - offset
            if notify_time.date() == today.date():
                should_notify = True
                occurrence_to_notify = start_time
                offset_str_to_notify = offset_str
                break
    else:
        # Handle repeating events
        try:
            rule = rrulestr(calendar_item.rrule, dtstart=calendar_item.start_time)
            max_offset_days = max(parse_offset(offset_str=o).days for o in offsets)
            latest_check_date = today + timedelta(days=max_offset_days)

            occurrences = rule.between(
                after=today, before=latest_check_date + timedelta(days=1), inc=True
            )

            for occurrence in occurrences:
                # Skip if this occurrence is cancelled
                # occurrence is a datetime, need to get just the date part
                if isinstance(occurrence, datetime):
                    occurrence_date = occurrence.date()
                else:
                    occurrence_date = occurrence
                if occurrence_date in cancelled_dates:
                    logger.debug(
                        f"Skipping cancelled occurrence {occurrence_date} for "
                        f"calendar item {calendar_item.calendar_item_id}"
                    )
                    continue

                for offset_str in offsets:
                    offset = parse_offset(offset_str=offset_str)
                    notify_time = occurrence - offset
                    if notify_time.date() == today.date():
                        should_notify = True
                        occurrence_to_notify = occurrence
                        offset_str_to_notify = offset_str
                        break

                if should_notify:
                    break
        except Exception as e:
            logger.error(
                f"Error parsing RRULE for calendar item "
                f"{calendar_item.calendar_item_id}: {str(e)}"
            )
            raise

    if not should_notify or not occurrence_to_notify or not offset_str_to_notify:
        return

    logger.info(
        f"Creating notification for calendar item {calendar_item.calendar_item_id} "
        f"(title: {calendar_item.title}, occurrence: {occurrence_to_notify}, "
        f"offset: {offset_str_to_notify})"
    )

    # Get users from assignments
    user_ids = await _get_users_from_assignments(db=db, calendar_item=calendar_item)

    if not user_ids:
        logger.warning(
            f"No users found for calendar item {calendar_item.calendar_item_id}"
        )
        return

    # Determine which users should receive notifications
    (
        users_to_notify_in_app,
        users_to_notify_email,
    ) = await determine_notification_recipients(
        db=db,
        project_id=str(calendar_item.project_id),
        notification_type_id=notification_type_id,
        severity=enumerations.NotificationSeverity.WARNING,
    )

    # Filter to only users who are assigned to this calendar item
    assigned_user_ids_set = set(user_ids)
    users_to_notify_in_app = [
        uid for uid in users_to_notify_in_app if uid in assigned_user_ids_set
    ]
    users_to_notify_email = [
        uid for uid in users_to_notify_email if uid in assigned_user_ids_set
    ]

    if not users_to_notify_in_app and not users_to_notify_email:
        logger.info(
            f"No users to notify for calendar item {calendar_item.calendar_item_id} "
            f"(after filtering by assignments and preferences)"
        )
        return

    # Create notification
    notification = await create_notification(
        db=db,
        project_id=calendar_item.project_id,
        notification_type_id=notification_type_id,
        data={
            "notification_type": "calendar reminder",
            "calendar_item_id": str(calendar_item.calendar_item_id),
            "title": calendar_item.title,
            "description": calendar_item.description,
            "start_time": occurrence_to_notify.isoformat(),
            "end_time": (
                calendar_item.end_time.isoformat() if calendar_item.end_time else None
            ),
            "all_day": calendar_item.all_day,
            "offset": offset_str_to_notify,
        },
        severity=enumerations.NotificationSeverity.WARNING,
    )
    summary["notifications_created"] += 1

    # Create in-app notification states
    for user_id in users_to_notify_in_app:
        try:
            await create_notification_state(
                db=db,
                notification_id=notification.notification_id,
                user_id=user_id,
                channel=enumerations.NotificationChannel.IN_APP,
            )
            summary["in_app_notifications"] += 1
        except Exception as e:
            logger.error(
                f"Failed to create in-app notification state for user {user_id}: "
                f"{str(e)}"
            )
            summary["errors"].append(
                f"Failed to create in-app notification state for user {user_id}: "
                f"{str(e)}"
            )

    # Send email notifications
    if users_to_notify_email:
        logger.info(
            f"Sending email notifications to {len(users_to_notify_email)} users "
            f"for calendar item {calendar_item.calendar_item_id}"
        )

        def get_email_kwargs_func(
            *,
            user_id: str,  # noqa: ARG001
            user_email: str,
            user_name: str,  # noqa: ARG001
        ) -> dict:
            """Build email kwargs for a user.

            Args:
                user_id: User ID.
                user_email: User email.
                user_name: User name.

            Returns:
                Email kwargs dict for SES send_email.
            """
            # Format occurrence date
            occurrence_date_str = occurrence_to_notify.strftime("%Y-%m-%d")

            # Render HTML body using Jinja2 template
            template = jinja_env.get_template("calendar_reminder.html")
            html_body = template.render(
                user_name=user_name,
                title=calendar_item.title,
                description=calendar_item.description or "",
                occurrence_date=occurrence_date_str,
                project_url="https://app.proximal.energy/portfolio/calendar",
            )

            return {
                "FromEmailAddress": "alerts@proximal.energy",
                "Destination": {
                    "ToAddresses": [user_email],
                },
                "Content": {
                    "Simple": {
                        "Subject": {"Data": f"Reminder: {calendar_item.title}"},
                        "Body": {
                            "Html": {"Data": html_body},
                        },
                    },
                },
            }

        # Send emails with rate limiting
        await send_notification_emails_with_rate_limit(
            db=db,
            user_ids=users_to_notify_email,
            get_email_kwargs_func=get_email_kwargs_func,
            notification_id=notification.notification_id,
            summary=dict(summary),
        )

    logger.info(
        f"Completed processing calendar item {calendar_item.calendar_item_id}: "
        f"{len(users_to_notify_in_app)} in-app, {len(users_to_notify_email)} email"
    )
