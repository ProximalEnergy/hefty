import datetime
import logging
import re
import urllib.parse
import uuid as uuid_lib
from pathlib import Path as PathLib
from typing import Annotated
from uuid import UUID

import boto3
from core.crud.admin.notifications import (
    create_notification,
    create_notification_state,
    get_notification_type_by_name,
)
from core.crud.admin.users import get_users
from core.crud.operational.projects import get_projects
from core.database import with_db_async
from core.db_query import OutputType
from core.utils.notifications import (
    determine_notification_recipients,
    send_notification_emails_with_rate_limit,
)
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import dependencies
from app._crud.projects import (
    event_chat_mutes as crud_event_chat_mutes,
)
from app._crud.projects import (
    event_message_images as crud_event_message_images,
)
from app._crud.projects import (
    event_messages as crud_event_messages,
)
from app.dependencies import (
    get_project_name_short_async,
)
from core import enumerations, models

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/event-messages",
    tags=["event_messages"],
)

# Batch router for operations that don't require a specific project
batch_router = APIRouter(
    prefix="/event-messages",
    tags=["event_messages"],
)

# Company theme color mapping (matches frontend CompanyThemeManager.ts)
COMPANY_THEME_CONFIG: dict[str, str] = {
    "catl": "blue",
    "cleanamps_energy": "cleanamps-energy-green",
    "desri": "desri-blue",
    "excelsior": "excelsior-blue",
    "first_solar": "red",
    "mccarthy": "mccarthy-red",
    "longroad_energy": "mccarthy-red",
    "origis_energy": "origis-blue",
    "strata": "orange",
    "swift_current_energy": "swift-blue",
    "terabase_energy": "terabase-blue",
    "lightsource_bp": "lightsource-bp-orange",
    "oriden": "oriden-green",
    "lydian_energy": "lydian-energy-blue",
}

# Theme color hex values (matches frontend themes.ts, using shade 7 as primary)
THEME_COLORS: dict[str, str] = {
    "proximal-blue": "#21B8F1",
    "desri-blue": "#3A68F5",
    "excelsior-blue": "#316090",
    "mccarthy-red": "#E0214C",
    "origis-blue": "#5B699D",
    "swift-blue": "#2186B5",
    "terabase-blue": "#394D6E",
    "lightsource-bp-orange": "#FE6623",
    "oriden-green": "#22C586",  # shade 7 from themes.ts
    "lydian-energy-blue": "#6072AA",  # shade 7 from themes.ts
    "cleanamps-energy-green": "#21B6B1",  # shade 7 from themes.ts
    "blue": "#228BE6",  # Mantine default blue
    "red": "#FA5252",  # Mantine default red
    "orange": "#FD7E14",  # Mantine default orange
    "green": "#51CF66",  # Mantine default green
}


def _get_company_theme_color(*, company_name_short: str | None) -> str:
    """Get the primary theme color for a company.

    Args:
        company_name_short: Description for company_name_short.
    """
    if not company_name_short:
        return "#21B8F1"  # Default proximal-blue

    theme_name = COMPANY_THEME_CONFIG.get(company_name_short, "proximal-blue")
    return THEME_COLORS.get(theme_name, "#21B8F1")  # Default to proximal-blue


# S3 Configuration for event chat images
EVENT_CHAT_IMAGES_BUCKET_NAME = "proximal-event-chat-images"
EVENT_CHAT_IMAGES_REGION_NAME = "us-east-2"
EVENT_CHAT_IMAGES_PRESIGNED_URL_EXPIRATION = 86400  # 24 hours

# Image upload constraints
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
}
MAX_IMAGE_SIZE_MB = 10
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024


# --- Pydantic Schemas ---
class EventMessageCreate(BaseModel):
    """todo"""

    event_id: int
    body: str
    parent_message_id: int | None = None
    private: bool = False


class EventMessage(BaseModel):
    """todo"""

    event_message_id: int
    event_id: int
    user_id: str
    body: str
    mentions: str | None
    parent_message_id: int | None
    created_at: datetime.datetime
    edited_at: datetime.datetime | None
    deleted_at: datetime.datetime | None
    image_s3_keys: str | None = None  # Comma-separated S3 keys for images
    private: bool = False


class EventMessageImage(BaseModel):
    """todo"""

    event_message_image_id: UUID
    event_message_id: int
    event_id: int
    s3_key: str
    filename: str
    content_type: str
    file_size: int  # bytes
    created_at: datetime.datetime


class EventChatMute(BaseModel):
    """todo"""

    event_id: int
    user_id: str
    muted_at: datetime.datetime


# --- Helper Functions ---
def _model_to_pydantic_message(*, model: models.EventMessage) -> EventMessage:
    """Convert database model to Pydantic schema.

    Args:
        model: Description for model.
    """
    # Get image_s3_keys from related images
    image_s3_keys = None
    if model.images:
        image_s3_keys = ",".join([img.s3_key for img in model.images])

    return EventMessage(
        event_message_id=model.event_message_id,
        event_id=model.event_id,
        user_id=model.user_id,
        body=model.body,
        mentions=model.mentions,
        parent_message_id=model.parent_message_id,
        created_at=model.created_at,
        edited_at=model.edited_at,
        deleted_at=model.deleted_at,
        image_s3_keys=image_s3_keys,
        private=model.private,
    )


# --- Mention Extraction ---
def extract_mentions(*, body: str) -> list[str]:
    """Extract @mentions from message body using regex.

    Args:
        body: Description for body.
    """
    pattern = r"@(\w+)"
    mentions = re.findall(pattern, body)
    return mentions


# --- Email Notification ---
async def send_event_chat_email(
    *,
    recipient_user_id: str,
    recipient_email: str,
    recipient_name: str,
    sender_name: str,
    event_id: int,
    message_body: str,
    event_url: str,
    is_first_message: bool,
    project_name: str | None = None,
    device_type_name: str | None = None,
    failure_mode_name: str | None = None,
    company_theme_color: str = "#21B8F1",
) -> None:
    """Send an email notification for an event chat message.

    Args:
        recipient_user_id: The user ID of the recipient (for logging/tracking)
        recipient_email: The email address of the recipient
        recipient_name: The name of the recipient
        sender_name: The name of the sender
        event_id: The event ID
        message_body: The message body
        event_url: The URL to view the event
        is_first_message: Whether this is the first message in the event
        project_name: Optional project name
        device_type_name: Optional device type name
        failure_mode_name: Optional failure mode name
        company_theme_color: Optional company theme color (defaults to proximal-blue)
    """
    # recipient_user_id is kept for API consistency and potential future use
    _ = recipient_user_id  # noqa: F841
    ses_client = boto3.client("sesv2", region_name="us-east-2")

    # Truncate message body for email preview
    message_preview = (
        message_body[:200] + "..." if len(message_body) > 200 else message_body
    )

    # Build subject line: <Project Name>: <Failure Mode> - <User Name> message
    # on Event #<event_id>
    subject_parts = []
    if project_name:
        subject_parts.append(project_name)
    if failure_mode_name:
        subject_parts.append(failure_mode_name)
    if subject_parts:
        subject = (
            f"{': '.join(subject_parts)} - {sender_name} message on Event #{event_id}"
        )
    else:
        subject = f"{sender_name} message on Event #{event_id}"

    # Determine the reason text based on whether it's the first message
    if is_first_message:
        reason_text = (
            "You're receiving this because a team member started a new "
            "conversation on this event chat."
        )
    else:
        reason_text = "You're receiving this because you've posted to this event chat."

    # Build event details section with company theme color
    # Lighten the theme color for background (add opacity effect using rgba
    # approximation)
    event_details_parts = []
    if project_name:
        event_details_parts.append(f"<strong>Project:</strong> {project_name}")
    if device_type_name:
        event_details_parts.append(f"<strong>Device Type:</strong> {device_type_name}")
    if failure_mode_name:
        event_details_parts.append(
            f"<strong>Failure Mode:</strong> {failure_mode_name}"
        )

    event_details_html = ""
    if event_details_parts:
        # Create a lighter version of the theme color for background
        # Convert hex to RGB and add opacity
        hex_color = company_theme_color.lstrip("#")
        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        bg_color = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.1)"

        event_details_html = f"""
        <div
            style="
                background-color: {bg_color};
                padding: 12px;
                border-radius: 5px;
                margin: 15px 0;
                border-left: 4px solid {company_theme_color};
            "
        >
            <p style="margin: 0; font-size: 14px; color: #333;">
                {"<br>".join(event_details_parts)}
            </p>
        </div>
        """

    html_body = f"""
    <html>
    <body>
        <p>Hi {recipient_name},</p>

        <p><strong>{sender_name}</strong> posted a new message on Event #{event_id}:</p>

        {event_details_html}

        <div
            style="
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            "
        >
            <p style="margin: 0; white-space: pre-wrap;">{message_preview}</p>
        </div>

        <p>
            <a
                href="{event_url}"
                style="
                    background-color: {company_theme_color};
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                "
            >
                View Event Chat
            </a>
        </p>

        <p style="color: #666; font-size: 12px; margin-top: 30px;">
            {reason_text}
            <a href="{event_url}&mute=true">Mute this conversation</a>
        </p>

        <p style="color: #666; font-size: 12px; margin-top: 15px;">
            To control email notifications for first messages on event chats per
            project, visit your
            <a
                href="https://app.proximal.energy/application-settings"
                style="color: {company_theme_color}; text-decoration: underline;"
            >
                Application Settings
            </a>.
        </p>
    </body>
    </html>
    """

    email_kwargs = {
        "FromEmailAddress": "proximal-chat@proximal.energy",
        "Destination": {
            "ToAddresses": [recipient_email],
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

    try:
        ses_client.send_email(**email_kwargs)
        logger.info(
            f"📧 Sent event chat email to {recipient_email} for event {event_id}"
        )
    except Exception as e:
        logger.error(f"Failed to send event chat email to {recipient_email}: {str(e)}")


def _build_event_chat_email_kwargs(
    *,
    recipient_email: str,
    recipient_name: str,
    sender_name: str,
    event_id: int,
    message_body: str,
    event_url: str,
    is_first_message: bool,
    project_name: str | None = None,
    device_type_name: str | None = None,
    failure_mode_name: str | None = None,
    company_theme_color: str = "#21B8F1",
) -> dict:
    """Build SES email kwargs for an event chat notification.

    Args:
        recipient_email: Recipient email address.
        recipient_name: Recipient display name.
        sender_name: Sender display name.
        event_id: Event ID.
        message_body: Message body (may be truncated in output).
        event_url: URL to the event chat.
        is_first_message: Whether this is the first message in the thread.
        project_name: Optional project name.
        device_type_name: Optional device type name.
        failure_mode_name: Optional failure mode name.
        company_theme_color: Hex color for email styling.

    Returns:
        Dict suitable for boto3 sesv2 send_email.
    """
    message_preview = (
        message_body[:200] + "..." if len(message_body) > 200 else message_body
    )
    subject_parts = []
    if project_name:
        subject_parts.append(project_name)
    if failure_mode_name:
        subject_parts.append(failure_mode_name)
    if subject_parts:
        subject = (
            f"{': '.join(subject_parts)} - {sender_name} message on Event #{event_id}"
        )
    else:
        subject = f"{sender_name} message on Event #{event_id}"
    reason_text = (
        "You're receiving this because a team member started a new "
        "conversation on this event chat."
        if is_first_message
        else ("You're receiving this because you've posted to this event chat.")
    )
    event_details_parts = []
    if project_name:
        event_details_parts.append(f"<strong>Project:</strong> {project_name}")
    if device_type_name:
        event_details_parts.append(f"<strong>Device Type:</strong> {device_type_name}")
    if failure_mode_name:
        event_details_parts.append(
            f"<strong>Failure Mode:</strong> {failure_mode_name}"
        )
    event_details_html = ""
    if event_details_parts:
        hex_color = company_theme_color.lstrip("#")
        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        bg_color = f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, 0.1)"
        event_details_html = f"""
        <div
            style="
                background-color: {bg_color};
                padding: 12px;
                border-radius: 5px;
                margin: 15px 0;
                border-left: 4px solid {company_theme_color};
            "
        >
            <p style="margin: 0; font-size: 14px; color: #333;">
                {"<br>".join(event_details_parts)}
            </p>
        </div>
        """
    html_body = f"""
    <html>
    <body>
        <p>Hi {recipient_name},</p>

        <p><strong>{sender_name}</strong> posted a new message on Event #{event_id}:</p>

        {event_details_html}

        <div
            style="
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            "
        >
            <p style="margin: 0; white-space: pre-wrap;">{message_preview}</p>
        </div>

        <p>
            <a
                href="{event_url}"
                style="
                    background-color: {company_theme_color};
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                "
            >
                View Event Chat
            </a>
        </p>

        <p style="color: #666; font-size: 12px; margin-top: 30px;">
            {reason_text}
            <a href="{event_url}&mute=true">Mute this conversation</a>
        </p>

        <p style="color: #666; font-size: 12px; margin-top: 15px;">
            To control email notifications for first messages on event chats per
            project, visit your
            <a
                href="https://app.proximal.energy/application-settings"
                style="color: {company_theme_color}; text-decoration: underline;"
            >
                Application Settings
            </a>.
        </p>
    </body>
    </html>
    """
    return {
        "FromEmailAddress": "proximal-chat@proximal.energy",
        "Destination": {"ToAddresses": [recipient_email]},
        "Content": {
            "Simple": {
                "Subject": {"Data": subject},
                "Body": {"Html": {"Data": html_body}},
            },
        },
    }


async def send_notifications_for_message(
    *,
    db: AsyncSession,
    project_db: AsyncSession,
    project_id: UUID,
    event_id: int,
    sender_user_id: str,
    sender_company_id: UUID,
    message_body: str,
    is_first_message: bool,
    is_private: bool = False,
) -> None:
    """Create notifications for event chat messages using the notifications framework.

    Rules:
    - First message: notify all users with project access (public) or company
      users with project access (private), filtered by notification prefs
    - Subsequent messages: notify users who have posted (NO preference filter)
      - Public follow-up: notify all users who posted
      - Private follow-up: notify only users from the same company who posted
    - Never notify the sender or muted users
    """
    users_who_posted = await crud_event_messages.get_users_who_posted_to_event(
        db=project_db, event_id=event_id
    )
    if is_first_message:
        # Build base query for users with project access
        stmt = (
            select(models.User)
            .join(
                models.UserProject,
                models.User.user_id == models.UserProject.user_id,
            )
            .where(models.UserProject.operational_project_id == project_id)
        )
        # Add company filter for private messages
        if is_private:
            stmt = stmt.where(models.User.company_id == sender_company_id)
        result = await db.execute(stmt)
        project_users_raw = result.scalars().all()
        event_chat_recipient_ids = {user.user_id for user in project_users_raw}
    else:
        # Follow-up messages: notify users who have posted
        if not users_who_posted:
            event_chat_recipient_ids = set()
        else:
            # Build base query filtering by users who posted
            user_id_stmt = select(models.User.user_id).where(
                models.User.user_id.in_(users_who_posted)
            )
            # Add company filter for private messages
            if is_private:
                user_id_stmt = user_id_stmt.where(
                    models.User.company_id == sender_company_id
                )
            result = await db.execute(user_id_stmt)
            user_ids = result.scalars().all()
            event_chat_recipient_ids = {str(user_id) for user_id in user_ids}

    event_chat_recipient_ids.discard(sender_user_id)
    mutes = await crud_event_chat_mutes.get_event_chat_mutes(
        db=project_db, event_id=event_id
    )
    muted_user_ids = {
        mute.user_id for mute in mutes if mute.user_id in event_chat_recipient_ids
    }
    event_chat_recipient_ids -= muted_user_ids

    notification_type_query = get_notification_type_by_name(
        name_long="event_chat_message"
    )
    notification_type = await notification_type_query.get_async(
        output_type=OutputType.SQLALCHEMY
    )
    if not notification_type:
        logger.warning(
            "Notification type 'event_chat_message' not found, skipping "
            "event chat notifications"
        )
        return

    if is_first_message:
        # First message: apply notification preferences
        (
            users_to_notify_in_app,
            users_to_notify_email,
        ) = await determine_notification_recipients(
            db=db,
            project_id=str(project_id),
            notification_type_id=notification_type.notification_type_id,
            severity=enumerations.NotificationSeverity.INFO,
        )

        recipients_in_app = [
            u for u in users_to_notify_in_app if u in event_chat_recipient_ids
        ]
        recipients_email = [
            u for u in users_to_notify_email if u in event_chat_recipient_ids
        ]
    else:
        # Follow-up messages: notify all participants (no preference filter)
        # All participants get both in-app and email notifications
        recipients_in_app = list(event_chat_recipient_ids)
        recipients_email = list(event_chat_recipient_ids)

    if not recipients_in_app and not recipients_email:
        logger.info(f"No recipients for event {event_id} notifications")
        return

    sender_users = await get_users(user_ids=[sender_user_id]).get_async(
        output_type=OutputType.SQLALCHEMY
    )
    sender_name = sender_users[0][0].name_long if sender_users else "Unknown User"

    project_name = None
    device_type_name = None
    failure_mode_name = None
    try:
        db_query = get_projects(project_ids=[project_id])
        rows = await db_query.get_async(output_type=OutputType.SQLALCHEMY)
        if rows:
            project_name = rows[0].name_long
        project_name_short = await get_project_name_short_async(project_id=project_id)
        if project_name_short:
            event_stmt = (
                select(models.Event)
                .options(
                    selectinload(models.Event.device).selectinload(
                        models.Device.device_type
                    ),
                    selectinload(models.Event.failure_mode),
                )
                .where(models.Event.event_id == event_id)
            )
            event_result = await project_db.execute(event_stmt)
            event: models.Event | None = event_result.scalar_one_or_none()
            if event:
                if event.device and event.device.device_type:
                    device_type_name = event.device.device_type.name_long
                if event.failure_mode:
                    failure_mode_name = event.failure_mode.name_long
    except Exception as e:
        logger.warning(f"Failed to fetch event details for event {event_id}: {e}")

    event_url = (
        "https://app.proximal.energy/projects/"
        f"{project_id}/events/event?eventId={event_id}"
    )
    message_preview = (
        message_body[:200] + "..." if len(message_body) > 200 else message_body
    )

    notification = await create_notification(
        db=db,
        project_id=project_id,
        notification_type_id=notification_type.notification_type_id,
        data={
            "notification_type": "event_chat_message",
            "event_id": event_id,
            "project_id": str(project_id),
            "sender_name": sender_name,
            "message_body": message_preview,
            "is_first_message": is_first_message,
            "device_type_name": device_type_name,
            "failure_mode_name": failure_mode_name,
        },
        severity=enumerations.NotificationSeverity.INFO,
    )

    for user_id in recipients_in_app:
        try:
            await create_notification_state(
                db=db,
                notification_id=notification.notification_id,
                user_id=user_id,
                channel=enumerations.NotificationChannel.IN_APP,
            )
        except Exception as e:
            logger.error(f"Failed to create in-app state for user {user_id}: {e}")

    if recipients_email:
        summary: dict = {"errors": []}

        def get_email_kwargs_func(
            *,
            user_id: str,  # noqa: ARG001 (required by send_notification_emails_with_rate_limit)
            user_email: str,
            user_name: str,
        ) -> dict:
            return _build_event_chat_email_kwargs(
                recipient_email=user_email,
                recipient_name=user_name,
                sender_name=sender_name,
                event_id=event_id,
                message_body=message_body,
                event_url=event_url,
                is_first_message=is_first_message,
                project_name=project_name,
                device_type_name=device_type_name,
                failure_mode_name=failure_mode_name,
            )

        await send_notification_emails_with_rate_limit(
            db=db,
            user_ids=recipients_email,
            get_email_kwargs_func=get_email_kwargs_func,
            notification_id=notification.notification_id,
            summary=summary,
        )


# --- API Endpoints ---
@router.get("")
async def get_event_messages(
    *,
    project_db: Annotated[AsyncSession, Depends(dependencies.get_project_db_async)],
    event_id: Annotated[int, Query(...)],
) -> list[EventMessage]:
    """Get all non-deleted messages for a specific event.

        Query Parameters:
            event_id: The ID of the event to get messages for

        Returns:
            List of event messages, ordered by created_at (ascending)

    Args:
        project_db: Description for project_db.
        event_id: Description for event_id.
    """
    message_models = await crud_event_messages.get_event_messages(
        db=project_db, event_id=event_id
    )

    return [_model_to_pydantic_message(model=msg) for msg in message_models]


@router.post("")
async def create_event_message(
    *,
    project_db: Annotated[AsyncSession, Depends(dependencies.get_project_db_async)],
    project_schema: Annotated[str, Depends(get_project_name_short_async)] = "",
    project_id: Annotated[UUID, Path(...)],
    message: EventMessageCreate,
    background_tasks: BackgroundTasks,
    user_data: Annotated[
        dependencies.interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
) -> EventMessage:
    """Create a new event message.

        - Extracts @mentions from the message body
        - Stores mentions as comma-separated usernames
        - Sends email notifications in the background to:
            - First message: all company users
            - Subsequent messages: users who have posted (excluding muted users)

        Request Body:
            event_id: The ID of the event
            body: The message content (may contain @mentions)

        Returns:
            The created event message

    Args:
        project_db: Description for project_db.
        project_schema: Description for project_schema.
        project_id: Description for project_id.
        message: Description for message.
        background_tasks: Description for background_tasks.
        user_data: Description for user_data.
        api_prod: Description for api_prod.
    """
    # Extract mentions from body
    mentioned_usernames = extract_mentions(body=message.body)

    # Check if this is the first message BEFORE creating (for notification logic)
    existing_messages = await crud_event_messages.get_event_messages(
        db=project_db, event_id=message.event_id
    )
    is_first_message = len(existing_messages) == 0

    # Create message in database
    message_model = await crud_event_messages.create_event_message(
        db=project_db,
        event_id=message.event_id,
        user_id=user_data.user_id,
        body=message.body,
        mentions=",".join(mentioned_usernames) if mentioned_usernames else None,
        parent_message_id=message.parent_message_id,
        private=message.private,
    )
    # Save the ID before commit (flush already populated it)
    message_id = message_model.event_message_id
    await project_db.commit()
    # Reload message with images relationship after commit
    reloaded_message_model = await crud_event_messages.get_event_message_by_id(
        event_message_id=message_id
    ).get_async(
        output_type=OutputType.SQLALCHEMY,
        schema=project_schema,
    )
    if not reloaded_message_model:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve created message"
        )

    event_message = _model_to_pydantic_message(model=reloaded_message_model)

    # Send notifications in background
    async def send_notifications_background():
        """Send notifications for the message in a background task."""
        async with with_db_async(schema=None) as db_session:
            project_name_short = await get_project_name_short_async(
                project_id=project_id
            )
            async with with_db_async(schema=project_name_short) as project_db_session:
                await send_notifications_for_message(
                    event_id=message.event_id,
                    sender_user_id=user_data.user_id,
                    sender_company_id=user_data.company_id,
                    message_body=message.body,
                    is_first_message=is_first_message,
                    is_private=message.private,
                    project_id=project_id,
                    db=db_session,
                    project_db=project_db_session,
                )

    background_tasks.add_task(send_notifications_background)

    return event_message


class EventMessageUpdate(BaseModel):
    """todo"""

    body: str
    image_ids: list[UUID] | None = (
        None  # List of image IDs to keep, in order matching placeholders
    )


@router.put("/{event_message_id}")
async def update_event_message(
    *,
    project_db: Annotated[AsyncSession, Depends(dependencies.get_project_db_async)],
    project_schema: Annotated[str, Depends(get_project_name_short_async)] = "",
    event_message_id: int,
    message: EventMessageUpdate,
    user_data: Annotated[
        dependencies.interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
) -> EventMessage:
    """Update an existing event message.

        Validates:
        - User owns the message
        - Message exists and is not deleted

        Request Body:
            body: The updated message content (may contain @mentions)

        Returns:
            The updated event message

    Args:
        project_db: Description for project_db.
        project_schema: Description for project_schema.
        event_message_id: Description for event_message_id.
        message: Description for message.
        user_data: Description for user_data.
    """
    # Extract mentions from body
    mentioned_usernames = extract_mentions(body=message.body)

    # Verify message exists and user owns it
    message_model = await crud_event_messages.get_event_message_by_id(
        event_message_id=event_message_id
    ).get_async(
        output_type=OutputType.SQLALCHEMY,
        schema=project_schema,
    )
    if not message_model:
        raise HTTPException(
            status_code=404, detail=f"Event message {event_message_id} not found"
        )

    if message_model.user_id != user_data.user_id:
        raise HTTPException(
            status_code=403, detail="You can only edit your own messages"
        )

    # Get all existing images for this message
    existing_images = await crud_event_message_images.get_event_message_images(
        db=project_db, event_message_id=event_message_id
    )

    # If image_ids is provided, delete images not in the list
    # This allows the frontend to specify exactly which images to keep
    if message.image_ids is not None:
        try:
            # Convert to UUID objects if needed (Pydantic may already convert them)
            image_ids_set = set()
            for img_id in message.image_ids:
                if isinstance(img_id, UUID):
                    image_ids_set.add(img_id)
                else:
                    # If it's a string, convert it
                    image_ids_set.add(UUID(img_id))
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting image IDs to UUIDs: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image ID format: {e}",
            )

        images_deleted = False
        for img in existing_images:
            if img.event_message_image_id not in image_ids_set:
                await crud_event_message_images.delete_event_message_image(
                    db=project_db,
                    event_message_image_id=img.event_message_image_id,
                    project_schema=project_schema,
                )
                images_deleted = True

        # Flush deletions before querying remaining keys
        if images_deleted:
            await project_db.flush()

    # Update message
    updated_message = await crud_event_messages.update_event_message(
        db=project_db,
        event_message_id=event_message_id,
        body=message.body,
        mentions=",".join(mentioned_usernames) if mentioned_usernames else None,
    )
    if not updated_message:
        raise HTTPException(status_code=500, detail="Failed to update message")

    # Always update image_s3_keys to reflect current state after any deletions
    # Get fresh list of remaining images after deletions
    remaining_keys = await crud_event_message_images.get_image_s3_keys_for_message(
        db=project_db, event_message_id=event_message_id
    )
    await crud_event_messages.update_event_message_image_s3_keys(
        db=project_db,
        event_message_id=event_message_id,
        image_s3_keys=",".join(remaining_keys) if remaining_keys else None,
    )

    await project_db.commit()

    # Reload message with images relationship after commit
    reloaded_message_model = await crud_event_messages.get_event_message_by_id(
        event_message_id=event_message_id
    ).get_async(
        output_type=OutputType.SQLALCHEMY,
        schema=project_schema,
    )
    if not reloaded_message_model:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve updated message"
        )

    event_message = _model_to_pydantic_message(model=reloaded_message_model)

    return event_message


@router.delete("/{event_message_id}")
async def delete_event_message(
    *,
    project_db: Annotated[AsyncSession, Depends(dependencies.get_project_db_async)],
    event_message_id: int,
    user_data: Annotated[
        dependencies.interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
) -> EventMessage:
    """Delete an existing event message (soft delete).

        Validates:
        - User owns the message
        - Message exists

        Returns:
            The deleted event message (with deleted_at set)

    Args:
        project_db: Description for project_db.
        event_message_id: Description for event_message_id.
        user_data: Description for user_data.
    """
    # Delete message (soft delete)
    deleted_message = await crud_event_messages.delete_event_message(
        db=project_db,
        event_message_id=event_message_id,
        user_id=user_data.user_id,
    )
    if not deleted_message:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Event message {event_message_id} not found or you don't have "
                "permission to delete it"
            ),
        )

    await project_db.commit()

    # Reload message with images relationship after commit
    # Note: get_event_message_by_id filters out deleted messages,
    # so we need to fetch it directly
    stmt = (
        select(models.EventMessage)
        .options(selectinload(models.EventMessage.images))
        .where(models.EventMessage.event_message_id == event_message_id)
    )
    result = await project_db.execute(stmt)
    reloaded_message_model = result.scalar_one_or_none()

    if not reloaded_message_model:
        raise HTTPException(
            status_code=500, detail="Failed to retrieve deleted message"
        )

    event_message = _model_to_pydantic_message(model=reloaded_message_model)

    return event_message


@router.post("/{event_id}/mute")
async def toggle_event_chat_mute(
    *,
    project_db: Annotated[AsyncSession, Depends(dependencies.get_project_db_async)],
    event_id: int,
    user_data: Annotated[
        dependencies.interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
) -> dict:
    """Toggle mute status for an event chat.

        Returns:
            {"muted": bool} - True if muted, False if unmuted

    Args:
        project_db: Description for project_db.
        event_id: Description for event_id.
        user_data: Description for user_data.
    """
    is_muted = await crud_event_chat_mutes.toggle_event_chat_mute(
        db=project_db, event_id=event_id, user_id=user_data.user_id
    )
    await project_db.commit()

    return {"muted": is_muted}


@router.get("/{event_id}/mute-status")
async def get_event_chat_mute_status(
    *,
    project_db: Annotated[AsyncSession, Depends(dependencies.get_project_db_async)],
    _: Annotated[None, Depends(dependencies.check_project_access_async)],
    event_id: int,
    user_data: Annotated[
        dependencies.interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
) -> dict:
    """Get mute status for an event chat.

        Returns:
            {"muted": bool} - True if muted, False if not muted

    Args:
        project_db: Project-scoped DB session (event_chat_mutes in project schema).
        event_id: Description for event_id.
        user_data: Description for user_data.
    """
    muted_query = crud_event_chat_mutes.is_event_chat_muted(
        event_id=event_id, user_id=user_data.user_id
    )
    is_muted = (
        await muted_query.get_async(
            executor=project_db, output_type=OutputType.SQLALCHEMY
        )
        is not None
    )

    return {"muted": is_muted}


# --- Image Upload Endpoints ---
def _validate_image_file(*, file: UploadFile) -> None:
    """Validate image file type and size.

    Args:
        file: Description for file.
    """
    # Check content type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
            ),
        )

    # Note: File size validation happens when reading the file content
    # since UploadFile.size might not be reliable


def _generate_image_s3_key(
    *, event_id: int, event_message_id: int, filename: str
) -> str:
    """Generate S3 key for an image.

    Args:
        event_id: Description for event_id.
        event_message_id: Description for event_message_id.
        filename: Description for filename.
    """
    # Sanitize filename (remove path components, keep only basename)
    safe_filename = PathLib(filename).name
    # Generate UUID to prevent collisions
    image_uuid = str(uuid_lib.uuid4())
    # Combine: event_id/message_id/uuid-filename
    return f"{event_id}/{event_message_id}/{image_uuid}-{safe_filename}"


def _generate_image_presigned_url(*, s3_key: str, filename: str | None = None) -> str:
    """Generate a presigned URL for an image.

        If filename is provided, includes response-content-disposition header
        to force download instead of displaying in browser.

    Args:
        s3_key: Description for s3_key.
        filename: Description for filename.
    """
    s3_client = boto3.client("s3", region_name=EVENT_CHAT_IMAGES_REGION_NAME)
    params = {
        "Bucket": EVENT_CHAT_IMAGES_BUCKET_NAME,
        "Key": s3_key,
    }

    # Add response-content-disposition to force download
    if filename:
        # URL encode the filename for the header
        encoded_filename = urllib.parse.quote(filename)
        params["ResponseContentDisposition"] = (
            f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}"
        )

    presigned_url = s3_client.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=EVENT_CHAT_IMAGES_PRESIGNED_URL_EXPIRATION,
    )
    return str(presigned_url)


@router.post("/{event_id}/images/{event_message_id}")
async def upload_event_message_image(
    *,
    project_db: Annotated[AsyncSession, Depends(dependencies.get_project_db_async)],
    project_schema: Annotated[str, Depends(get_project_name_short_async)] = "",
    event_id: int,
    event_message_id: int,
    file: UploadFile = File(...),
) -> dict:
    """Upload an image for an event message.

        Validates:
        - User has access to the event (via message ownership or event access)
        - File is a valid image type (jpeg, png, gif, webp)
        - File size is within limit (10MB)

        Returns:
            {
                "event_message_image_id": UUID,
                "s3_key": str,
                "filename": str,
                "content_type": str,
                "file_size": int,
                "presigned_url": str
            }

    Args:
        project_db: Description for project_db.
        project_schema: Description for project_schema.
        event_id: Description for event_id.
        event_message_id: Description for event_message_id.
        file: Description for file.
    """
    # Validate file type
    _validate_image_file(file=file)

    # Verify message exists and belongs to this event
    message = await crud_event_messages.get_event_message_by_id(
        event_message_id=event_message_id
    ).get_async(
        output_type=OutputType.SQLALCHEMY,
        schema=project_schema,
    )
    if not message or message.event_id != event_id:
        raise HTTPException(
            status_code=404,
            detail=(f"Event message {event_message_id} not found for event {event_id}"),
        )

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file size
    if file_size > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File size ({file_size / 1024 / 1024:.2f}MB) exceeds "
                f"maximum allowed size ({MAX_IMAGE_SIZE_MB}MB)"
            ),
        )

    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    # Generate S3 key
    filename = file.filename or "image"
    s3_key = _generate_image_s3_key(
        event_id=event_id,
        event_message_id=event_message_id,
        filename=filename,
    )

    # Upload to S3
    s3_client = boto3.client("s3", region_name=EVENT_CHAT_IMAGES_REGION_NAME)
    try:
        s3_client.put_object(
            Bucket=EVENT_CHAT_IMAGES_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type or "image/jpeg",
        )
    except Exception as e:
        logger.error(f"Failed to upload image to S3: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to upload image. Please try again."
        )

    # Create image record in database
    image_model = await crud_event_message_images.create_event_message_image(
        db=project_db,
        event_message_id=event_message_id,
        event_id=event_id,
        s3_key=s3_key,
        filename=filename,
        content_type=file.content_type or "image/jpeg",
        file_size=file_size,
    )
    # Save the ID before commit (flush already populated it)
    image_id = image_model.event_message_image_id
    await project_db.commit()

    # Update message's image_s3_keys (computed field)
    existing_keys = await crud_event_message_images.get_image_s3_keys_for_message(
        db=project_db, event_message_id=event_message_id
    )
    await crud_event_messages.update_event_message_image_s3_keys(
        db=project_db,
        event_message_id=event_message_id,
        image_s3_keys=",".join(existing_keys),
    )
    await project_db.commit()

    # Generate presigned URL
    presigned_url = _generate_image_presigned_url(s3_key=s3_key)

    return {
        "event_message_image_id": image_id,
        "s3_key": s3_key,
        "filename": filename,
        "content_type": file.content_type or "image/jpeg",
        "file_size": file_size,
        "presigned_url": presigned_url,
    }


@router.get("/{event_id}/images/{image_id}/url")
async def get_event_message_image_url(
    *,
    project_schema: Annotated[str, Depends(get_project_name_short_async)] = "",
    event_id: int,
    image_id: UUID,
) -> dict:
    """Get a presigned URL for an event message image.

        Validates user has access to the event before generating URL.

        Returns:
            {"presigned_url": str, "s3_key": str}

    Args:
        project_db: Description for project_db.
        project_schema: Description for project_schema.
        event_id: Description for event_id.
        image_id: Description for image_id.
    """
    # Find image record
    image = await crud_event_message_images.get_event_message_image_by_id(
        event_message_image_id=image_id
    ).get_async(
        output_type=OutputType.SQLALCHEMY,
        schema=project_schema,
    )

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Verify image belongs to this event
    if image.event_id != event_id:
        raise HTTPException(status_code=404, detail="Image not found")

    # Generate presigned URL with download disposition
    presigned_url = _generate_image_presigned_url(
        s3_key=image.s3_key, filename=image.filename
    )

    return {
        "presigned_url": presigned_url,
        "s3_key": image.s3_key,
    }


@router.get("/{event_id}/messages/{event_message_id}/images")
async def get_event_message_images(
    *,
    project_db: Annotated[AsyncSession, Depends(dependencies.get_project_db_async)],
    project_schema: Annotated[str, Depends(get_project_name_short_async)] = "",
    event_id: int,
    event_message_id: int,
) -> list[dict]:
    """Get all images for an event message with presigned URLs.

        Returns:
            List of image objects with presigned URLs

    Args:
        project_db: Description for project_db.
        project_schema: Description for project_schema.
        event_id: Description for event_id.
        event_message_id: Description for event_message_id.
    """
    # Verify message exists and belongs to this event
    message = await crud_event_messages.get_event_message_by_id(
        event_message_id=event_message_id
    ).get_async(
        output_type=OutputType.SQLALCHEMY,
        schema=project_schema,
    )
    if not message or message.event_id != event_id:
        raise HTTPException(status_code=404, detail="Event message not found")

    # Get images for this message
    image_models = await crud_event_message_images.get_event_message_images(
        db=project_db, event_message_id=event_message_id
    )

    # Generate presigned URLs for each image
    result = []
    for image in image_models:
        # For display, don't force download (use filename=None)
        presigned_url = _generate_image_presigned_url(s3_key=image.s3_key)
        result.append(
            {
                "event_message_image_id": image.event_message_image_id,
                "s3_key": image.s3_key,
                "filename": image.filename,
                "content_type": image.content_type,
                "file_size": image.file_size,
                "presigned_url": presigned_url,
            }
        )

    return result
