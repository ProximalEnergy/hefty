"""Weather alert notification system for NWS forecast polygons."""

import logging
import traceback
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import cast

from geoalchemy2.shape import to_shape
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models
from core.crud.admin.notifications import (
    create_notification,
    create_notification_state,
    get_recent_notification,
)
from core.crud.admin.users import get_users as get_users_crud
from core.crud.operational.projects import get_projects
from core.database import AsyncSessionLambda, async_engine
from core.db_query import OutputType
from core.domain.gis.providers.nws import NWSProvider
from core.utils.notifications import (
    determine_notification_recipients,
    ensure_notification_states_exist,
    send_notification_email,
    severity_to_numeric,
)
from core.utils.user_management import get_user_email_from_clerk

logger = logging.getLogger(__name__)

# Severity thresholds based on probability percentage
# INFO < 15%, WARNING < 30%, CRITICAL >= 30%
SEVERITY_THRESHOLDS = {
    enumerations.NotificationSeverity.INFO: 15.0,
    enumerations.NotificationSeverity.WARNING: 30.0,
    enumerations.NotificationSeverity.CRITICAL: 100.0,
}

# NWS / summary / payload keys -> notification enum (DB notification_type_id)
VALID_WEATHER_TYPES: dict[str, enumerations.NotificationType] = {
    "hail": enumerations.NotificationType.HAIL,
    "tornado": enumerations.NotificationType.TORNADO,
    "wind": enumerations.NotificationType.WIND,
    "fire": enumerations.NotificationType.FIRE,
}

# User-facing labels in emails (risk wording, not NWS "alert")
WEATHER_TYPE_EMAIL_DISPLAY = {
    "fire": "Fire Risk",
    "hail": "Hail Risk",
    "tornado": "Tornado Risk",
    "wind": "Wind Risk",
}

# Treat as "same storm" only if last notification was within this many days
SAME_EVENT_WINDOW_DAYS = 2


def probability_to_severity(*, probability: float) -> enumerations.NotificationSeverity:
    """Convert probability percentage to notification severity.

    Args:
        probability: Probability percentage (0-100).

    Returns:
        Notification severity level.
    """
    if probability >= SEVERITY_THRESHOLDS[enumerations.NotificationSeverity.WARNING]:
        return enumerations.NotificationSeverity.CRITICAL
    elif probability >= SEVERITY_THRESHOLDS[enumerations.NotificationSeverity.INFO]:
        return enumerations.NotificationSeverity.WARNING
    else:
        return enumerations.NotificationSeverity.INFO


def fire_code_to_severity(*, code: int) -> enumerations.NotificationSeverity:
    """Convert fire alert numeric code to notification severity.

    Args:
        code: Fire alert numeric code (5=Elevated, 8=Critical, 10=Extreme).

    Returns:
        Notification severity level.
    """
    if code == 10:  # Extreme
        return enumerations.NotificationSeverity.CRITICAL
    elif code == 8:  # Critical
        return enumerations.NotificationSeverity.WARNING
    elif code == 5:  # Elevated
        return enumerations.NotificationSeverity.INFO
    else:
        # Default to INFO for unknown codes
        return enumerations.NotificationSeverity.INFO


def fire_code_to_display_name(*, code: int) -> str:
    """Convert fire alert numeric code to display name.

    Args:
        code: Fire alert numeric code (5=Elevated, 8=Critical, 10=Extreme).

    Returns:
        Display name for the fire alert level.
    """
    if code == 10:
        return "Extreme"
    elif code == 8:
        return "Critical"
    elif code == 5:
        return "Elevated"
    else:
        return f"Code {code}"


async def check_weather_alerts(*, api_prod: bool = True) -> dict:
    """Check NWS polygons and create notifications for affected projects.

    Args:
        api_prod: Whether running in production (affects Clerk API calls).

    Returns:
        Dictionary with summary of notifications created.
    """
    logger.info("Starting weather alert check function")
    summary = {
        "projects_checked": 0,
        "notifications_created": 0,
        "emails_sent": 0,
        "in_app_notifications": 0,
        "polygons_retrieved": {
            "hail": 0,
            "tornado": 0,
            "wind": 0,
            "fire": 0,
        },
        "errors": [],
    }

    async with AsyncSessionLambda() as db:
        try:
            logger.info("Connected to database, fetching projects")
            # Get all active projects using DbQuery
            projects_query = get_projects(
                project_status_type_ids=[enumerations.ProjectStatusType.ACTIVE],
            )
            projects_raw = await projects_query.get_async(
                output_type=OutputType.SQLALCHEMY
            )
            # Type assertion: get_projects_async returns DbQuery[models.Project],
            # so get_async with SQLALCHEMY returns Sequence[models.Project]
            projects = cast(Sequence[models.Project], projects_raw)
            summary["projects_checked"] = len(projects)
            logger.info(f"Found {len(projects)} active projects")

            # Initialize NWS provider
            nws_provider = NWSProvider()

            # Check each weather type
            # Note: fire alerts return (polygon, category, day) while others
            # return (polygon, probability, day)
            weather_types = [
                (
                    "hail",
                    nws_provider.get_hail_outlook_polygons,
                    False,
                ),  # False = uses probability
                ("tornado", nws_provider.get_tornado_outlook_polygons, False),
                ("wind", nws_provider.get_wind_outlook_polygons, False),
                (
                    "fire",
                    nws_provider.get_fire_outlook_polygons,
                    True,
                ),  # True = uses category
            ]

            for weather_type, get_polygons_func, is_fire_alert in weather_types:
                try:
                    polygons = get_polygons_func()
                    summary["polygons_retrieved"][weather_type] = len(polygons)  # type: ignore[index,arg-type]
                    logger.info(
                        f"Retrieved {len(polygons)} {weather_type} polygons from NWS"  # type: ignore[arg-type]
                    )

                    # Debug: Log polygon details for fire alerts
                    if is_fire_alert and polygons:
                        logger.info("Fire polygons details:")
                        for i, (polygon, value, day) in enumerate(
                            polygons[:3]  # type: ignore[index]
                        ):  # Log first 3 polygons
                            bounds = (
                                polygon.bounds
                                if hasattr(polygon, "bounds")
                                else "no bounds"
                            )
                            logger.info(
                                f"  Polygon {i + 1}: code={value}, "
                                f"day={day}, bounds={bounds}"
                            )

                    # Check each project against polygons
                    for project in projects:
                        try:
                            await _check_project_against_polygons(
                                db=db,
                                project=project,
                                weather_type=weather_type,
                                polygons=polygons,  # type: ignore[arg-type]
                                is_fire_alert=is_fire_alert,
                                api_prod=api_prod,
                                summary=summary,
                            )
                        except Exception as e:
                            error_msg = (
                                f"Error checking project {project.project_id} "
                                f"for {weather_type}: {str(e)}"
                            )
                            logger.error(error_msg)
                            summary["errors"].append(error_msg)  # type: ignore[attr-defined]  # type: ignore[attr-defined]  # type: ignore[attr-defined]

                except Exception as e:
                    error_msg = f"Error fetching {weather_type} polygons: {str(e)}"
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)  # type: ignore[attr-defined]  # type: ignore[attr-defined]

        except Exception as e:
            error_msg = f"Error in check_weather_alerts: {str(e)}"
            logger.error(error_msg)
            summary["errors"].append(error_msg)  # type: ignore[attr-defined]

    # Ensure notification states exist for all created notifications
    # This is a safety net in case async errors prevented state creation
    # during processing
    await ensure_notification_states_exist(
        notification_types=tuple(VALID_WEATHER_TYPES.values()),
    )

    # Ensure the async engine is disposed to avoid un-awaited cancellation warnings
    try:
        await async_engine.dispose()
    except Exception as e:
        logger.warning("Error disposing async engine: %s", e)

    return summary


async def _check_project_against_polygons(
    *,
    db: AsyncSession,
    project: models.Project,
    weather_type: str,
    polygons: list[tuple[Polygon, float | int, str]],
    is_fire_alert: bool,
    api_prod: bool,
    summary: dict,
) -> None:
    """Check if a project is within any polygons and create notifications if needed.

    Args:
        db: Database session.
        project: Project model.
        weather_type: Type of weather (tornado, wind, fire, hail).
        polygons: List of tuples (polygon, value, day) where value is
            probability or severity code.
        is_fire_alert: Whether this is a fire alert (uses severity codes
            instead of probabilities).
        api_prod: Whether running in production.
        summary: Summary dictionary to update.
    """
    notification_type = VALID_WEATHER_TYPES.get(weather_type)
    if notification_type is None:
        logger.warning(f"Unknown weather type: {weather_type}")
        return
    notification_type_id = notification_type.value
    # Extract project coordinates from point
    if not project.point:
        logger.info(f"Project {project.project_id} has no point data, skipping")
        return

    try:
        point_shape = to_shape(project.point)  # type: ignore[arg-type]
        project_point = ShapelyPoint(point_shape.x, point_shape.y)
        logger.info(
            f"Processing project {project.project_id} at coordinates "
            f"({project_point.x}, {project_point.y}) for {weather_type}"
        )
    except Exception as e:
        logger.warning(
            f"Could not extract coordinates from project {project.project_id}: {str(e)}"
        )
        return

    # Find the highest severity polygon that contains this project
    max_probability = 0.0
    max_severity_numeric = 0
    matching_polygon = None
    matching_day = "unknown"
    matching_value: float | int | None = (
        None  # Will be probability (float) or severity code (int)
    )
    nws_provider = NWSProvider()

    for polygon, value, day in polygons:
        if nws_provider.point_in_polygon(point=project_point, polygon=polygon):
            if is_fire_alert:
                # For fire alerts, value is a severity code (int)
                severity = fire_code_to_severity(code=int(value))
                severity_numeric = severity_to_numeric(severity=severity)
                logger.info(
                    f"Project {project.project_id} inside fire polygon: "
                    f"code={value}, severity={severity.value}, day={day}"
                )
                if severity_numeric > max_severity_numeric:
                    max_severity_numeric = severity_numeric
                    matching_polygon = polygon
                    matching_day = day
                    matching_value = value
            else:
                # For other alerts, value is a probability float
                probability = float(value)
                if probability > max_probability:
                    max_probability = probability
                    matching_polygon = polygon
                    matching_day = day
                    matching_value = probability

    # If project is not in any polygon, skip
    if (
        (is_fire_alert and max_severity_numeric == 0)
        or (not is_fire_alert and max_probability == 0.0)
        or matching_polygon is None
    ):
        logger.info(
            f"Project {project.project_id} not within any {weather_type} "
            f"polygons, skipping"
        )
        return

    # Determine severity and display value
    if is_fire_alert:
        if matching_value is None or not isinstance(matching_value, int):
            raise ValueError(f"Invalid matching_value for fire alert: {matching_value}")
        severity = fire_code_to_severity(code=matching_value)
        display_value: float | str = fire_code_to_display_name(
            code=matching_value
        )  # "Critical", "Extreme", etc.
    else:
        severity = probability_to_severity(probability=max_probability)
        display_value = max_probability  # probability percentage

    # Check if we should create a notification.
    # Create if: no previous notification, or last one is outside same-event
    # window (new event), or severity increased within the window.
    recent_notification_query = get_recent_notification(
        project_id=project.project_id,
        notification_type_id=notification_type_id,
    )
    recent_notification = await recent_notification_query.get_async(
        output_type=OutputType.SQLALCHEMY
    )

    if recent_notification:
        cutoff = datetime.now(UTC) - timedelta(days=SAME_EVENT_WINDOW_DAYS)
        created_at = recent_notification.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        within_same_event_window = created_at >= cutoff

        recent_severity_numeric = severity_to_numeric(
            severity=recent_notification.severity
        )
        current_severity_numeric = severity_to_numeric(severity=severity)

        logger.info(
            f"Project {project.project_id} has recent {weather_type} notification "
            f"(severity: {recent_notification.severity.value} -> {severity.value}, "
            f"numeric: {recent_severity_numeric} -> {current_severity_numeric}, "
            f"within_same_event_window: {within_same_event_window})"
        )

        if (
            within_same_event_window
            and current_severity_numeric <= recent_severity_numeric
        ):
            logger.info(
                f"Same-event window and severity did not increase for project "
                f"{project.project_id} (current: {current_severity_numeric} <= "
                f"recent: {recent_severity_numeric}), skipping notification"
            )
            return
    else:
        logger.info(
            f"Project {project.project_id} has no recent {weather_type} notification, "
            f"proceeding with severity {severity.value}"
        )

    # Determine which users should be notified and how
    (
        users_to_notify_in_app,
        users_to_notify_email,
    ) = await determine_notification_recipients(
        db=db,
        project_id=str(project.project_id),
        notification_type_id=notification_type_id,
        severity=severity,
    )

    logger.info(
        f"Project {project.project_id} notification recipients determined: "
        f"{len(users_to_notify_in_app)} in-app, {len(users_to_notify_email)} email"
    )

    should_create_notification = (
        len(users_to_notify_in_app) > 0 or len(users_to_notify_email) > 0
    )

    if not should_create_notification:
        logger.warning(
            f"No users to notify for project {project.project_id} with {weather_type} "
            f"alert (severity: {severity.value}). This could be due to: "
            f"1) User preferences disabled, 2) Notification type defaults disabled, "
            f"3) Severity threshold too high, or "
            f"4) No users linked to project companies."
        )
        return

    # Create one notification per project if any user should be notified
    notification = None
    if should_create_notification:
        logger.info(
            f"Creating {weather_type} notification for project "
            f"{project.project_id} (severity: {severity.value}) - "
            f"{len(users_to_notify_in_app)} in-app, "
            f"{len(users_to_notify_email)} email"
        )
        notification = await create_notification(
            db=db,
            project_id=project.project_id,
            notification_type_id=notification_type_id,
            data={
                "weather_type": weather_type,
                "value": display_value,
                "severity": severity.value,
                "day": matching_day,
            },
            severity=severity,
        )
        summary["notifications_created"] += 1

        # Create in-app notification states for all qualifying users
        for user_id in users_to_notify_in_app:
            try:
                logger.info(
                    f"Creating in-app notification state for user {user_id} "
                    f"on notification {notification.notification_id}"
                )
                await create_notification_state(
                    db=db,
                    notification_id=notification.notification_id,
                    user_id=user_id,
                    channel=enumerations.NotificationChannel.IN_APP,
                )
                summary["in_app_notifications"] += 1
            except Exception as e:
                logger.error(
                    f"Exception during in-app notification state creation "
                    f"for user {user_id}: {str(e)}"
                )
                summary["errors"].append(
                    f"Exception creating in-app notification state "
                    f"for user {user_id}: {str(e)}"
                )

        # Send email notifications to all qualifying users
        logger.info(
            f"Sending emails to {len(users_to_notify_email)} users: "
            f"{users_to_notify_email}"
        )
        for user_id in users_to_notify_email:
            logger.info(f"Attempting to send email notification to user {user_id}")
            try:
                await _send_weather_alert_email_to_user(
                    db=db,
                    user_id=user_id,
                    project=project,
                    notification=notification,
                    weather_type=weather_type,
                    value=display_value,
                    severity=severity,
                    is_fire_alert=is_fire_alert,
                    api_prod=api_prod,
                    summary=summary,
                )
                logger.info(
                    f"Successfully processed email notification for user {user_id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to send email notification to user {user_id}: {str(e)}"
                )
                summary["errors"].append(
                    f"Failed to send email to user {user_id}: {str(e)}"
                )


async def _send_weather_alert_email_to_user(
    *,
    db: AsyncSession,
    user_id: str,
    project: models.Project,
    notification: models.Notification,
    weather_type: str,
    value: float | str,
    severity: enumerations.NotificationSeverity,
    is_fire_alert: bool,
    api_prod: bool,  # noqa: ARG001
    summary: dict,
) -> None:
    """Send email notification to a specific user.

    Args:
        db: Database session.
        user_id: User ID.
        project: Project model.
        notification: Notification model.
        weather_type: Type of weather.
        value: Probability percentage (float) or severity display name (str).
        severity: Severity level.
        is_fire_alert: Whether this is a fire alert.
        api_prod: Whether running in production.
        summary: Summary dictionary to update.
    """
    logger.info(f"Getting email for user {user_id}")
    user_email = await get_user_email_from_clerk(user_id=user_id)
    if not user_email:
        logger.warning(
            f"Could not get email for user {user_id} from Clerk - no email returned"
        )
        summary["errors"].append(f"No email found for user {user_id}")
        return

    logger.info(f"Sending {weather_type} email to user {user_id} at {user_email}")

    # Get user name
    users_query = get_users_crud(user_ids=[user_id])
    users = await users_query.get_async(output_type=OutputType.SQLALCHEMY)
    if not users:
        logger.warning(f"Could not find user {user_id}")
        return

    user = users[0][0]
    # Explicitly convert to plain strings to avoid any database object access
    user_name = str(user.name_long)

    # Extract all values before calling email function to avoid lazy loading issues
    project_name = str(project.name_long)
    project_id_str = str(project.project_id)  # Extract project ID for URL
    notification_id = int(notification.notification_id)  # Extract notification ID
    severity_value = str(severity.value.upper())  # Extract enum value as string

    # Determine severity color
    severity_colors = {
        enumerations.NotificationSeverity.INFO: "#2196F3",  # Blue
        enumerations.NotificationSeverity.WARNING: "#FF9800",  # Orange
        enumerations.NotificationSeverity.CRITICAL: "#F44336",  # Red
    }
    severity_color = str(severity_colors.get(severity, "#2196F3"))

    # Convert value to string to avoid any database access
    if is_fire_alert:
        value_str = str(value)
    else:
        value_str = f"{float(value):.1f}%"

    # Build email content before calling email function to avoid
    # any async/db issues. Use .format() instead of f-strings to ensure
    # all values are evaluated as plain types
    try:
        weather_type_display = WEATHER_TYPE_EMAIL_DISPLAY.get(
            weather_type,
            f"{weather_type.capitalize()} Risk",
        )
        label_text = "Category" if is_fire_alert else "Probability"
        subject = f"Weather Risk: {weather_type_display} Warning for {project_name}"
        project_url = f"https://app.proximal.energy/projects/{project_id_str}"
        html_body = f"""<html>
<body>
    <p>Hi {user_name},</p>

    <p>We detected a <strong>{weather_type_display}</strong> forecast that may
    affect your project:</p>

    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;
    margin: 20px 0; border-left: 4px solid {severity_color};">
        <p style="margin: 0; font-size: 16px;"><strong>Project:</strong>
        {project_name}</p>
        <p style="margin: 0; font-size: 16px;"><strong>Weather Type:</strong>
        {weather_type_display}</p>
        <p style="margin: 0; font-size: 16px;"><strong>{label_text}:</strong>
        {value_str}</p>
        <p style="margin: 0; font-size: 16px;"><strong>Severity:</strong>
        <span style="color: {severity_color}; font-weight: bold;">
        {severity_value}</span></p>
    </div>

    <p>
        <a href="{project_url}" style="background-color: #21B8F1; color: white;
        padding: 10px 20px; text-decoration: none; border-radius: 5px;
        display: inline-block;">View Project</a>
    </p>

    <p style="color: #666; font-size: 12px; margin-top: 30px;">
        You can manage your weather risk notification preferences in your
        <a href="https://app.proximal.energy/application-settings"
        style="color: #21B8F1; text-decoration: underline;">
        Application Settings</a>.
    </p>
</body>
</html>"""

        email_kwargs = {
            "FromEmailAddress": "alerts@proximal.energy",
            "Destination": {
                "ToAddresses": [user_email],
            },
            "Content": {
                "Simple": {
                    "Subject": {"Data": subject},
                    "Body": {
                        "Html": {"Data": html_body},
                    },
                },
            },
        }
    except Exception as e:
        logger.error(f"Error building email content: {str(e)}")
        raise

    # Send email using the shared utility
    logger.info(f"Calling send_notification_email for {user_email}")
    try:
        await send_notification_email(
            db=db,
            user_id=user_id,
            recipient_email=user_email,
            notification_id=notification_id,
            email_kwargs=email_kwargs,
            summary=summary,
        )
        logger.info(f"send_notification_email completed successfully for {user_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {user_email}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
