import base64
import logging
from typing import Annotated

from core.crud.admin.users import get_user
from core.db_query import OutputType
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies
from app.domain.internal_comms.comms import (
    CommunicationChannel,
    send_feedback_notification,
)
from app.domain.linear_integration import create_linear_issue
from core import models

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/feedback",
    tags=["feedback"],
    dependencies=[Depends(dependencies.get_user_data_async)],
)


@router.post("")
async def create_feedback(
    user_id: Annotated[str, Form(...)],
    email: Annotated[str, Form(...)],
    subject: Annotated[str, Form(...)],
    url: Annotated[str, Form(...)],
    comment: Annotated[str, Form(...)],
    screenshot: Annotated[UploadFile | None, File()] = None,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """todo

    Args:
        user_id: TODO: describe.
        email: TODO: describe.
        subject: TODO: describe.
        url: TODO: describe.
        comment: TODO: describe.
        screenshot: TODO: describe.
        db: TODO: describe.
    """
    screenshot_content = None
    screenshot_data_uri = None
    if screenshot:
        screenshot_content = await screenshot.read()
        encoded_content = base64.b64encode(screenshot_content).decode("utf-8")
        screenshot_data_uri = f"data:{screenshot.content_type};base64,{encoded_content}"

    feedback = models.Feedback(
        user_id=user_id,
        subject=subject,
        url=url,
        comment=comment,
        screenshot=screenshot_content if screenshot else None,
        screenshot_filename=screenshot.filename if screenshot else None,
        screenshot_mimetype=screenshot.content_type if screenshot else None,
    )
    # Get user name from database if available
    user_name = "Unknown"
    try:
        user = await get_user(user_id=user_id).get_async(
            output_type=OutputType.SQLALCHEMY
        )
        if user and user.name_long:
            user_name = user.name_long
    except Exception as e:
        logger.warning(f"Failed to get user name for feedback: {e}")

    # Send feedback to Linear
    issue_id = await create_linear_issue(
        title=f"Feedback: {subject}",
        description=comment,
        user_email=email,
        url=url,
        screenshot_data_uri=screenshot_data_uri,
    )

    # Send feedback to Google Chat
    send_feedback_notification(
        user_name_long=user_name,
        feedback=feedback,
        channel=CommunicationChannel.GOOGLE_CHAT,
        issue_id=issue_id,
    )
