"""Weather alert notification system for NWS forecast polygons."""

import logging
import os
import traceback
from collections.abc import Sequence
from typing import Literal, TypedDict, cast

from geoalchemy2.shape import to_shape
from jinja2 import Environment, FileSystemLoader, select_autoescape
from shapely.geometry import Point as ShapelyPoint
from shapely.geometry import Polygon
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models
from core.crud.admin.notifications import (
    create_notification,
    create_notification_state,
    get_notification_type_by_name,
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

# Setup Jinja2 environment for email templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)

# Valid weather types (used for validation)
VALID_WEATHER_TYPES = {"hail", "tornado", "wind", "fire"}

WeatherType = Literal["hail", "tornado", "wind", "fire"]


class PolygonsRetrievedSummary(TypedDict):
    hail: int
    tornado: int
    wind: int
    fire: int


class WeatherAlertsSummary(TypedDict):
    projects_checked: int
    notifications_created: int
    emails_sent: int
    in_app_notifications: int
    polygons_retrieved: PolygonsRetrievedSummary
    errors: list[str]


# Fire alert codes
FIRE_CODE_EXTREME = 10
FIRE_CODE_CRITICAL = 8
FIRE_CODE_ELEVATED = 5

FIRE_CODE_SEVERITY_MAP = {
    FIRE_CODE_EXTREME: enumerations.NotificationSeverity.CRITICAL,
    FIRE_CODE_CRITICAL: enumerations.NotificationSeverity.WARNING,
    FIRE_CODE_ELEVATED: enumerations.NotificationSeverity.INFO,
}

FIRE_CODE_DISPLAY_NAME_MAP = {
    FIRE_CODE_EXTREME: "Extreme",
    FIRE_CODE_CRITICAL: "Critical",
    FIRE_CODE_ELEVATED: "Elevated",
}


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
    return FIRE_CODE_SEVERITY_MAP.get(code, enumerations.NotificationSeverity.INFO)


def fire_code_to_display_name(*, code: int) -> str:
    """Convert fire alert numeric code to display name.

    Args:
        code: Fire alert numeric code (5=Elevated, 8=Critical, 10=Extreme).

    Returns:
        Display name for the fire alert level.
    """
    return FIRE_CODE_DISPLAY_NAME_MAP.get(code, f"Code {code}")


async def check_weather_alerts(*, api_prod: bool = True) -> WeatherAlertsSummary:
    """Check NWS polygons and create notifications for affected projects.

    Args:
        api_prod: Whether running in production (affects Clerk API calls).

    Returns:
        Dictionary with summary of notifications created.
    """
    logger.info("Starting weather alert check function")
    summary: WeatherAlertsSummary = {
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
            # Note: fire alerts return (polygon, category, day) while others return
            # (polygon, probability, day)
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
                    polygons_raw = get_polygons_func()
                    polygons = cast(list, polygons_raw)
                    summary["polygons_retrieved"][cast(WeatherType, weather_type)] = (
                        len(polygons)
                    )
                    logger.info(
                        f"Retrieved {len(polygons)} {weather_type} polygons from NWS"
                    )

                    # Debug: Log polygon details for fire alerts
                    if is_fire_alert and polygons:
                        logger.info("Fire polygons details:")
                        for i, (polygon, value, day) in enumerate(
                            polygons[:3]
                        ):  # Log first 3 polygons
                            bounds = (
                                polygon.bounds
                                if hasattr(polygon, "bounds")
                                else "no bounds"
                            )
                            logger.info(
                                f"  Polygon {i + 1}: code={value}, day={day}, "
                                f"bounds={bounds}"
                            )

                    # Check each project against polygons
                    for project in projects:
                        try:
                            await _check_project_against_polygons(
                                db=db,
                                project=project,
                                weather_type=weather_type,
                                polygons=polygons,
                                is_fire_alert=is_fire_alert,
                                api_prod=api_prod,
                                summary=summary,
                                nws_provider=nws_provider,
                            )
                        except Exception as e:
                            error_msg = (
                                f"Error checking project {project.project_id} "
                                f"for {weather_type}: {str(e)}"
                            )
                            logger.error(error_msg)
                            summary["errors"].append(error_msg)

                except Exception as e:
                    error_msg = f"Error fetching {weather_type} polygons: {str(e)}"
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Error in check_weather_alerts: {str(e)}"
            logger.error(error_msg)
            summary["errors"].append(error_msg)

    # Ensure notification states exist for all created notifications
    # This is a safety net in case async errors prevented state creation
    # during processing
    await ensure_notification_states_exist()

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
    summary: WeatherAlertsSummary,
    nws_provider: NWSProvider,
) -> None:
    """Check if a project is within any polygons and create notifications if needed.

    Args:
        db: Database session.
        project: Project model.
        weather_type: Type of weather (tornado, wind, fire, hail).
        polygons: List of tuples (polygon, value, day) where value is probability
            or severity code.
        is_fire_alert: Whether this is a fire alert (uses severity codes instead
            of probabilities).
        api_prod: Whether running in production.
        summary: Summary dictionary to update.
        nws_provider: NWS provider instance.
    """
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

    # Get notification type (weather_type is the same as the database name_long value)
    if weather_type not in VALID_WEATHER_TYPES:
        logger.warning(f"Unknown weather type: {weather_type}")
        return

    notification_type_query = get_notification_type_by_name(name_long=weather_type)
    notification_type = await notification_type_query.get_async(
        output_type=OutputType.SQLALCHEMY
    )
    if not notification_type:
        logger.warning(f"Notification type '{weather_type}' not found in database")
        return

    # Check if we should create a notification
    # Only create if severity increased or no previous notification
    recent_notification_query = get_recent_notification(
        project_id=project.project_id,
        notification_type_id=notification_type.notification_type_id,
    )
    recent_notification = await recent_notification_query.get_async(
        output_type=OutputType.SQLALCHEMY
    )

    if recent_notification:
        # Only create if severity increased
        recent_severity_numeric = severity_to_numeric(
            severity=recent_notification.severity
        )
        current_severity_numeric = severity_to_numeric(severity=severity)

        logger.info(
            f"Project {project.project_id} has recent {weather_type} notification "
            f"(severity: {recent_notification.severity.value} -> {severity.value}, "
            f"numeric: {recent_severity_numeric} -> {current_severity_numeric})"
        )

        if current_severity_numeric <= recent_severity_numeric:
            # Severity didn't increase, skip
            logger.info(
                f"Severity did not increase for project {project.project_id} "
                f"(current: {current_severity_numeric} <= "
                f"recent: {recent_severity_numeric}), "
                f"skipping notification"
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
        notification_type_id=notification_type.notification_type_id,
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
            f"Creating {weather_type} notification for project {project.project_id} "
            f"(severity: {severity.value}) - {len(users_to_notify_in_app)} in-app, "
            f"{len(users_to_notify_email)} email"
        )
        notification = await create_notification(
            db=db,
            project_id=project.project_id,
            notification_type_id=notification_type.notification_type_id,
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
                    f"Exception during in-app notification state creation for user "
                    f"{user_id}: {str(e)}"
                )
                summary["errors"].append(
                    f"Exception creating in-app notification state for user {user_id}: "
                    f"{str(e)}"
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
    api_prod: bool,
    summary: WeatherAlertsSummary,
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
    logger.info(f"Getting email for user {user_id} (api_prod={api_prod})")
    user_email = await get_user_email_from_clerk(user_id=user_id, api_prod=api_prod)
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

    # Build email content before calling email function to avoid any async/db issues
    try:
        weather_type_display = str(weather_type.capitalize())
        label_text = "Category" if is_fire_alert else "Probability"
        subject = f"Weather Alert: {weather_type_display} Warning for {project_name}"
        project_url = f"https://app.proximal.energy/projects/{project_id_str}"

        # Render HTML body using Jinja2 template
        template = jinja_env.get_template("weather_alert.html")
        html_body = template.render(
            user_name=user_name,
            weather_type_display=weather_type_display,
            severity_color=severity_color,
            project_name=project_name,
            label_text=label_text,
            value_str=value_str,
            severity_value=severity_value,
            project_url=project_url,
        )

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
            user_name=user_name,
            notification_id=notification_id,
            api_prod=api_prod,
            email_kwargs=email_kwargs,
            summary=cast(dict, summary),
        )
        logger.info(f"send_notification_email completed successfully for {user_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {user_email}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
