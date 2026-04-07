"""Shared notification utilities for creating and managing notifications."""

import asyncio
import copy
import logging
from collections.abc import Callable, Sequence
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models
from core.crud.admin.notifications import (
    create_notification_state,
    get_notification_preferences_for_project,
)
from core.crud.admin.users import get_users
from core.database import AsyncSessionLambda
from core.db_query import OutputType
from core.utils.user_management import get_user_email_from_clerk

logger = logging.getLogger(__name__)

# Maximum concurrent email sends to stay under SES rate limits
# SES default production limit is 14 emails/second, using 10 for safety
MAX_CONCURRENT_EMAIL_SENDS = 10

# Semaphore to limit concurrent email sends
_email_send_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EMAIL_SENDS)


def severity_to_numeric(*, severity: enumerations.NotificationSeverity) -> int:
    """Convert severity to numeric value for comparison.

    Args:
        severity: Notification severity.

    Returns:
        Numeric value (1=INFO, 2=WARNING, 3=CRITICAL).
    """
    mapping = {
        enumerations.NotificationSeverity.INFO: 1,
        enumerations.NotificationSeverity.WARNING: 2,
        enumerations.NotificationSeverity.CRITICAL: 3,
    }
    return mapping.get(severity, 1)


async def determine_notification_recipients(
    *,
    db: AsyncSession,
    project_id: str,
    notification_type_id: int,
    severity: enumerations.NotificationSeverity,
) -> tuple[list[str], list[str]]:
    """Determine which users should receive notifications and via which channels.

    Args:
        db: Database session.
        project_id: Project ID.
        notification_type_id: Notification type ID.
        severity: Notification severity level.

    Returns:
        Tuple of (users_to_notify_in_app, users_to_notify_email).
    """
    # Get all users with access to this project via user_projects table
    # This matches how the rest of the platform determines project access
    stmt = (
        select(models.User)
        .join(models.UserProject, models.User.user_id == models.UserProject.user_id)
        .where(models.UserProject.operational_project_id == UUID(project_id))
    )
    result = await db.execute(stmt)
    all_users_raw = result.scalars().all()
    all_users = [
        (user,) for user in all_users_raw
    ]  # Convert to tuple format for consistency
    if not all_users:
        logger.info(
            f"No users found with access to project {project_id} via "
            f"user_projects table"
        )
        return [], []

    # Get explicit notification preferences for this project and type
    explicit_preferences_query = get_notification_preferences_for_project(
        project_id=project_id,
        notification_type_id=notification_type_id,
    )
    explicit_preferences = await explicit_preferences_query.get_async(
        output_type=OutputType.SQLALCHEMY
    )

    # Create a map of user_id -> preferences for quick lookup
    preferences_map = {pref.user_id: pref for pref in explicit_preferences}

    # Get notification type to access defaults
    stmt_notification_type = select(models.NotificationType).where(
        models.NotificationType.notification_type_id == notification_type_id
    )
    result_notification_type = await db.execute(stmt_notification_type)
    notification_type = result_notification_type.scalar_one_or_none()

    users_to_notify_in_app = []
    users_to_notify_email = []
    severity_numeric = severity_to_numeric(severity=severity)

    logger.info(
        f"Determining notification recipients for project {project_id}, "
        f"notification_type_id {notification_type_id}, severity {severity.value} "
        f"(numeric: {severity_numeric}), {len(all_users)} total users, "
        f"{len(explicit_preferences)} with explicit preferences"
    )

    if notification_type:
        logger.info(
            f"Notification type defaults: "
            f"in_app_enabled={notification_type.in_app_enabled_default}, "
            f"email_enabled={notification_type.email_enabled_default}, "
            f"in_app_severity={notification_type.in_app_severity_default}, "
            f"email_severity={notification_type.email_severity_default}"
        )

    for user_tuple in all_users:
        user = user_tuple[0]
        user_id = user.user_id

        # Check if user has explicit preferences
        if user_id in preferences_map:
            # Use explicit preferences
            preference = preferences_map[user_id]

            min_in_app_numeric = severity_to_numeric(
                severity=preference.in_app_min_severity
            )
            min_email_numeric = severity_to_numeric(
                severity=preference.email_min_severity
            )

            logger.debug(
                f"User {user_id} has explicit preferences: "
                f"in_app_enabled={preference.in_app_enabled}, "
                f"email_enabled={preference.email_enabled}, "
                f"in_app_min_severity={preference.in_app_min_severity.value} "
                f"(numeric: {min_in_app_numeric}), "
                f"email_min_severity={preference.email_min_severity.value} "
                f"(numeric: {min_email_numeric})"
            )

            if preference.in_app_enabled and severity_numeric >= min_in_app_numeric:
                users_to_notify_in_app.append(user_id)
                logger.debug(f"User {user_id} added to in-app notifications")

            if preference.email_enabled and severity_numeric >= min_email_numeric:
                users_to_notify_email.append(user_id)
                logger.debug(f"User {user_id} added to email notifications")
        else:
            # Use notification type defaults
            if notification_type:
                min_in_app_numeric = severity_to_numeric(
                    severity=notification_type.in_app_severity_default
                    or enumerations.NotificationSeverity.INFO
                )
                min_email_numeric = severity_to_numeric(
                    severity=notification_type.email_severity_default
                    or enumerations.NotificationSeverity.INFO
                )

                logger.debug(
                    f"User {user_id} using defaults: "
                    f"in_app_enabled={notification_type.in_app_enabled_default}, "
                    f"email_enabled={notification_type.email_enabled_default}, "
                    f"min_severity: in_app={min_in_app_numeric}, "
                    f"email={min_email_numeric}"
                )

                if (
                    notification_type.in_app_enabled_default
                    and severity_numeric >= min_in_app_numeric
                ):
                    users_to_notify_in_app.append(user_id)
                    logger.debug(
                        f"User {user_id} added to in-app notifications (defaults)"
                    )

                if (
                    notification_type.email_enabled_default
                    and severity_numeric >= min_email_numeric
                ):
                    users_to_notify_email.append(user_id)
                    logger.debug(
                        f"User {user_id} added to email notifications (defaults)"
                    )

    logger.info(
        f"Notification recipients determined: {len(users_to_notify_in_app)} in-app, "
        f"{len(users_to_notify_email)} email"
    )

    return users_to_notify_in_app, users_to_notify_email


async def ensure_notification_states_exist(
    *,
    notification_types: Sequence[enumerations.NotificationType],
) -> None:
    """Ensure notifications of given types have notification states created.

    This is a safety net to handle cases where async errors or other issues
    prevented notification states from being created during the main processing.

    Args:
        notification_types: Only notifications with these type IDs are
            considered.
    """
    if not notification_types:
        return

    type_ids = [t.value for t in notification_types]

    async with AsyncSessionLambda() as db:
        try:
            # Find notifications that don't have any notification states
            stmt = (
                select(models.Notification)
                .outerjoin(
                    models.NotificationState,
                    models.Notification.notification_id
                    == models.NotificationState.notification_id,
                )
                .where(
                    models.NotificationState.notification_id.is_(None),
                    models.Notification.notification_type_id.in_(type_ids),
                )
            )
            result = await db.execute(stmt)
            notifications_without_states = result.scalars().all()

            logger.info(
                f"Found {len(notifications_without_states)} notifications "
                f"without states (notification_type_ids={type_ids})"
            )

            for notification in notifications_without_states:
                logger.info(
                    f"Creating missing states for notification "
                    f"{notification.notification_id}"
                )

                # Get notification preferences for this project and type
                preferences_query = get_notification_preferences_for_project(
                    project_id=notification.project_id,
                    notification_type_id=notification.notification_type_id,
                )
                preferences = await preferences_query.get_async(
                    output_type=OutputType.SQLALCHEMY
                )

                if preferences:
                    # Use explicit preferences
                    for preference in preferences:
                        severity_numeric = severity_to_numeric(
                            severity=notification.severity
                        )
                        min_in_app_numeric = severity_to_numeric(
                            severity=preference.in_app_min_severity
                        )
                        min_email_numeric = severity_to_numeric(
                            severity=preference.email_min_severity
                        )

                        # Create in-app state if conditions met
                        if (
                            preference.in_app_enabled
                            and severity_numeric >= min_in_app_numeric
                        ):
                            try:
                                await create_notification_state(
                                    db=db,
                                    notification_id=notification.notification_id,
                                    user_id=preference.user_id,
                                    channel=enumerations.NotificationChannel.IN_APP,
                                )
                                logger.info(
                                    f"Created missing in-app state for user "
                                    f"{preference.user_id} on notification "
                                    f"{notification.notification_id}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Failed to create missing in-app state for user "
                                    f"{preference.user_id}: {str(e)}"
                                )

                        # Create email state if conditions met
                        if (
                            preference.email_enabled
                            and severity_numeric >= min_email_numeric
                        ):
                            try:
                                await create_notification_state(
                                    db=db,
                                    notification_id=notification.notification_id,
                                    user_id=preference.user_id,
                                    channel=enumerations.NotificationChannel.EMAIL,
                                )
                                logger.info(
                                    f"Created missing email state for user "
                                    f"{preference.user_id} on notification "
                                    f"{notification.notification_id}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Failed to create missing email state for user "
                                    f"{preference.user_id}: {str(e)}"
                                )
                else:
                    # Use default settings - get all users with access to the project
                    # via user_projects table
                    stmt_users = (
                        select(models.User)
                        .join(
                            models.UserProject,
                            models.User.user_id == models.UserProject.user_id,
                        )
                        .where(
                            models.UserProject.operational_project_id
                            == notification.project_id
                        )
                    )
                    result_users = await db.execute(stmt_users)
                    users_raw = result_users.scalars().all()
                    users = [(user,) for user in users_raw]  # Convert to tuple format

                    if users:
                        # Create in-app states for all users (default behavior)
                        for user_tuple in users:
                            user = user_tuple[0]
                            try:
                                await create_notification_state(
                                    db=db,
                                    notification_id=notification.notification_id,
                                    user_id=user.user_id,
                                    channel=enumerations.NotificationChannel.IN_APP,
                                )
                                logger.info(
                                    f"Created missing default in-app state for "
                                    f"user {user.user_id} on notification "
                                    f"{notification.notification_id}"
                                )
                            except Exception as e:
                                logger.error(
                                    f"Failed to create missing default state for "
                                    f"user {user.user_id}: {str(e)}"
                                )

        except Exception as e:
            logger.error(f"Error in ensure_notification_states_exist: {str(e)}")
        finally:
            await db.close()


async def send_notification_email(
    *,
    db: AsyncSession,
    user_id: str,
    recipient_email: str,
    notification_id: int,
    email_kwargs: dict,
    summary: dict | None = None,
) -> None:
    """Send a notification email to a user.

    Args:
        db: Database session.
        user_id: User ID.
        recipient_email: Recipient email address.
        notification_id: Notification ID.
        email_kwargs: Pre-built email kwargs dict for SES send_email.
        summary: Optional summary dictionary to update with email count and errors.
    """
    logger.info(f"Sending notification email to user {user_id} at {recipient_email}")

    # Run the synchronous boto3 call in an executor to avoid blocking the event loop
    # and prevent SQLAlchemy async context issues
    def _send_email_sync(*, email_data: dict) -> None:
        """Send email in a separate thread to avoid SQLAlchemy async context issues.

        Args:
            email_data: Pre-built email kwargs dict for SES send_email.
        """
        ses_client = boto3.client("sesv2", region_name="us-east-2")
        ses_client.send_email(**email_data)

    try:
        # Deep copy the email_kwargs to ensure no references to database objects
        email_data = copy.deepcopy(email_kwargs)

        # Use to_thread for Python 3.9+, fallback to run_in_executor for older versions
        try:
            await asyncio.to_thread(_send_email_sync, email_data=email_data)
        except AttributeError:
            # Fallback for Python < 3.9
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: _send_email_sync(email_data=email_data)
            )
        logger.info(f"Sent notification email to {recipient_email}")

        # Create notification state for email
        try:
            await create_notification_state(
                db=db,
                notification_id=notification_id,
                user_id=user_id,
                channel=enumerations.NotificationChannel.EMAIL,
            )
            if summary is not None:
                summary["emails_sent"] = summary.get("emails_sent", 0) + 1
            logger.info(
                f"Created email notification state for user {user_id} "
                f"on notification {notification_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create email notification state for user {user_id} "
                f"on notification {notification_id}: {str(e)}"
            )
            if summary is not None:
                summary["errors"].append(
                    f"Failed to create email notification state for user {user_id}: "
                    f"{str(e)}"
                )
    except ClientError as e:
        error_msg = str(e.response.get("Error", {}).get("Message", str(e)))
        logger.error(f"AWS SES error sending email to {recipient_email}: {error_msg}")
        if summary is not None:
            summary["errors"].append(
                f"Failed to send email to user {user_id}: {error_msg}"
            )
        raise
    except Exception as e:
        logger.error(f"Unexpected error sending email to {recipient_email}: {str(e)}")
        if summary is not None:
            summary["errors"].append(
                f"Failed to send email to user {user_id}: {str(e)}"
            )
        raise


async def send_notification_emails_with_rate_limit(
    *,
    db: AsyncSession,
    user_ids: list[str],
    get_email_kwargs_func: Callable[..., dict],
    notification_id: int,
    summary: dict,
) -> None:
    """Send notification emails to multiple users with rate limiting.

    Args:
        db: Database session.
        user_ids: List of user IDs to send emails to.
        get_email_kwargs_func: Function that takes (user_id, user_email, user_name)
            and returns email_kwargs dict.
        notification_id: Notification ID.
        summary: Summary dictionary to update with email counts and errors.
    """
    if not user_ids:
        return

    logger.info(f"Sending notification emails to {len(user_ids)} users")

    async def _send_with_rate_limit(*, user_id: str) -> None:
        """Send email with semaphore-based rate limiting.

        Args:
            user_id: User ID to send email to.
        """
        async with _email_send_semaphore:
            try:
                # Get user email
                user_email = await get_user_email_from_clerk(user_id=user_id)
                if not user_email:
                    logger.warning(
                        f"Could not get email for user {user_id} from Clerk - "
                        f"no email returned"
                    )
                    summary["errors"].append(f"No email found for user {user_id}")
                    return

                # Get user name
                users_query = get_users(user_ids=[user_id])
                users = await users_query.get_async(output_type=OutputType.SQLALCHEMY)
                if not users:
                    logger.warning(f"Could not find user {user_id}")
                    return

                user = users[0][0]
                user_name = str(user.name_long)

                # Get email kwargs from the provided function
                email_kwargs = get_email_kwargs_func(
                    user_id=user_id, user_email=user_email, user_name=user_name
                )

                await send_notification_email(
                    db=db,
                    user_id=user_id,
                    recipient_email=user_email,
                    notification_id=notification_id,
                    email_kwargs=email_kwargs,
                    summary=summary,
                )
            except Exception as e:
                # Log error but don't raise - we want other emails to continue
                logger.error(f"Failed to send email to user {user_id}: {str(e)}")
                summary["errors"].append(
                    f"Failed to send email to user {user_id}: {str(e)}"
                )

    # Send all emails in parallel with rate limiting
    tasks = [_send_with_rate_limit(user_id=user_id) for user_id in user_ids]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Log summary
    emails_sent_count = summary.get("emails_sent", 0)
    errors_count = len(summary.get("errors", []))
    logger.info(
        f"Email sending complete: {emails_sent_count} emails sent, "
        f"{errors_count} errors encountered"
    )
