from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import dependencies, interfaces, utils
from app.core.internal_comms.comms import (
    CommunicationChannel,
    send_project_creation_notification,
)

router = APIRouter(
    prefix="/internal-comms",
    tags=["internal-communications"],
    include_in_schema=utils.get_include_in_schema(),
)


@router.post(
    "/project-creation-notification",
    dependencies=[Depends(dependencies.requires_admin_async)],
)
def send_project_creation_notification_endpoint(
    *,
    request: dict,
    user_data: interfaces.UserData = Depends(dependencies.get_user_data_async),
    db: Session = Depends(dependencies.get_db),
) -> dict:
    """
    Send a notification that a new project has been created.

    This endpoint sends notifications through the specified communication channel
    when a new project is created in the system.

    Args:
        request: The notification request containing project details
        user_data: Authenticated user data
        db: Database session

    Returns:
        ProjectCreationNotificationResponse: Success status and message

    Raises:
        HTTPException: 403 if user lacks admin permissions
    """

    success = send_project_creation_notification(
        project_name=request.get("project_name", ""),
        created_by=request.get("created_by", ""),
        created_by_company=request.get("created_by_company", ""),
        channel=CommunicationChannel(
            request.get("channel", CommunicationChannel.GOOGLE_CHAT)
        ),
    )

    if success:
        return {"message": "Success"}
    else:
        raise HTTPException(status_code=500, detail="Internal server error")
