import base64
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies
from app._crud.admin.users import get_user
from app.core.internal_comms.comms import (
    CommunicationChannel,
    send_feedback_notification,
)
from app.core.linear_integration import create_linear_issue
from core import models

router = APIRouter(
    prefix="/feedback",
    tags=["feedback"],
    dependencies=[Depends(dependencies.get_user_data_async)],
)


@router.post("/")
async def create_feedback(
    user_id: Annotated[str, Form()] = ...,  # type: ignore
    email: Annotated[str, Form()] = ...,  # type: ignore
    subject: Annotated[str, Form()] = ...,  # type: ignore
    url: Annotated[str, Form()] = ...,  # type: ignore
    comment: Annotated[str, Form()] = ...,  # type: ignore
    screenshot: Annotated[UploadFile | None, File()] = None,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
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
    # Get user name from db
    user = await get_user(db=db, user_id=user_id)
    if user:
        user_name_long = user.name_long or "Unknown"
    else:
        user_name_long = "Unknown"

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
        user_name_long=user_name_long,
        feedback=feedback,
        channel=CommunicationChannel.GOOGLE_CHAT,
        issue_id=issue_id,
    )
