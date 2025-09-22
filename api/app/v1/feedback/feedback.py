from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies
from app._crud.admin.feedback import create_feedback as crud_create_feedback
from app._crud.admin.users import get_user
from app.core.internal_comms.comms import (
    CommunicationChannel,
    send_feedback_notification,
)
from core import models

router = APIRouter(
    prefix="/feedback",
    tags=["feedback"],
    dependencies=[Depends(dependencies.get_user_data_async)],
)


@router.post("/")
async def create_feedback(
    user_id: Annotated[str, Form()] = ...,  # type: ignore
    subject: Annotated[str, Form()] = ...,  # type: ignore
    url: Annotated[str, Form()] = ...,  # type: ignore
    comment: Annotated[str, Form()] = ...,  # type: ignore
    screenshot: Annotated[UploadFile | None, File()] = None,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    feedback = models.Feedback(
        user_id=user_id,
        subject=subject,
        url=url,
        comment=comment,
        screenshot=screenshot.file.read() if screenshot else None,
        screenshot_filename=screenshot.filename if screenshot else None,
        screenshot_mimetype=screenshot.content_type if screenshot else None,
    )

    feedback_db = await crud_create_feedback(db, feedback=feedback)

    # Get user name
    user = await get_user(db=db, user_id=user_id)
    if user:
        user_name_long = user.name_long or "Unknown"
    else:
        user_name_long = "Unknown"

    send_feedback_notification(
        user_name_long=user_name_long,
        feedback=feedback_db,
        channel=CommunicationChannel.GOOGLE_CHAT,
    )
