from enum import StrEnum

from core.models import Feedback

from app.domain.internal_comms.comms_gchat import send_google_chat_message
from app.logger import logger


class CommunicationChannel(StrEnum):
    """Enum for available communication channels"""

    GOOGLE_CHAT = "google_chat"


def send_project_creation_notification(
    *,
    project_name: str,
    created_by: str,
    created_by_company: str,
    channel: CommunicationChannel,
) -> bool:
    """
    Send a notification that a new project has been created

    Args:
        project_name: Name of the created project
        created_by: User who created the project
        created_by_company: Company the user belongs to
        channel: Communication channel to use (defaults to GOOGLE_CHAT)

    Returns:
        bool: True if notification was sent successfully, False otherwise
    """

    match channel:
        case CommunicationChannel.GOOGLE_CHAT:
            webhook_url = "https://chat.googleapis.com/v1/spaces/AAQARB4NlwY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=583d8_DdQio48kmpJTYe0hyTth4dxqAfFMbxgJWwVrA"
            text = f"""
            Project: {project_name} has been created by
            {created_by} @ ({created_by_company}).
            """
            try:
                send_google_chat_message(
                    message=text,
                    webhook_url=webhook_url,
                )
                return True
            except Exception as e:
                logger.error(f"Failed to send notification via Google Chat: {e}")
                return False
        case _:
            logger.error(f"Unsupported communication channel: {channel}")
            return False


def send_feedback_notification(
    *,
    user_name_long: str,
    feedback: Feedback,
    channel: CommunicationChannel,
    issue_id: str | None = None,
):
    match channel:
        case CommunicationChannel.GOOGLE_CHAT:
            webhook_url = "https://chat.googleapis.com/v1/spaces/AAQAkqNNa48/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=4cUB-LNkgLEDFyHHHxe0nYPIvrP9DqM5cl1eRXnpuT0"
            url = f"https://app.proximal.energy{feedback.url}" if feedback.url else ""
            screenshot_included = feedback.screenshot_filename is not None
            linear_issue_url = (
                f"https://linear.app/proximal/issue/{issue_id}" if issue_id else ""
            )
            text = (
                f"💬 {user_name_long}\n"
                + (f"🔗 <{url}|Link>\n" if url else "")
                + (
                    f"📝 <{linear_issue_url}|Linear Issue>\n"
                    if linear_issue_url
                    else ""
                )
                + f"🆔 {feedback.feedback_id}\n"
                + f"*{feedback.subject}*\n"
                + f"{feedback.comment}"
                + ("\n🖼️ Screenshot Included" if screenshot_included else "")
            )
            try:
                send_google_chat_message(
                    message=text,
                    webhook_url=webhook_url,
                )
                return True
            except Exception as e:
                logger.error(f"Failed to send notification via Google Chat: {e}")
                return False
