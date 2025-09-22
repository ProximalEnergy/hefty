from datetime import datetime
from typing import Annotated
from uuid import UUID

import pytz
import sentry_sdk
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import dependencies, interfaces
from app._crud.operational.cmms_permissions import get_cmms_permissions_by_project_id
from app._utils.aws import get_secret
from app.core.cmms.cmms import CMMSSession, CMMSTicket
from app.core.cmms.cmms_registry import CMMS_SESSION_MAP

router = APIRouter(prefix="/projects/{project_id}/cmms-tickets", tags=["cmms-tickets"])


class CMMSMetadata(BaseModel):
    integration_configured: bool


class CMMSResponse(BaseModel):
    metadata: CMMSMetadata
    data: list[CMMSTicket]


@router.get("/", response_model=CMMSResponse)
async def get_cmms_tickets(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project_db: Annotated[
        Session,
        Depends(dependencies.get_project_db),
    ],  # will be needed when incorperating device data
    user: Annotated[interfaces.UserData, Depends(dependencies.get_user_data_async)],
    start: str | None = None,
    end: str | None = None,
    device_ids: Annotated[list[int] | None, Query()] = None,
):
    """
    Pulls the first 50 tickets for each CMMS provider.

    Parameters:
    -----------
    project_id : UUID
        The project identifier
    db : Session
        Database session
    project_db : Session
        Project database session
    user : interfaces.UserData
        To get the company id
    start : Optional[str]
        The start date of the tickets
    end : Optional[str]
        The end date of the tickets
    device_ids : Optional[List[int]]
        The list of device ids to filter the tickets by
    """

    integration_configured = False

    cmms_permissions = await get_cmms_permissions_by_project_id(
        db=db,
        company_id=user.company_id,
        project_id=project_id,
        can_view=True,
    )

    cmms_device_ids = None

    if device_ids is not None:
        cmms_devices = core.crud.project.cmms_devices.get_project_cmms_devices(
            project_db=project_db,
            cmms_integration_ids=[
                cmms_permission.cmms_integration.cmms_integration_id
                for cmms_permission in cmms_permissions
            ],
            device_ids=device_ids,
        ).models()

        # asset ids according to the CMMS provider
        cmms_device_ids = list(
            set([cmms_device.cmms_device_id for cmms_device in cmms_devices]),
        )

    tickets = []

    for cmms_permission in cmms_permissions:
        # if there is at least one element in cmms_permissions, then the
        # integration is considered configured
        try:
            integration_configured = True

            secret = get_secret(
                secret_name=(
                    f"cmms_integrations/cmms_integration_id/"
                    f"{cmms_permission.cmms_integration.cmms_integration_id}"
                ),
            )

            cmms_name = cmms_permission.cmms_integration.cmms_provider.name_short
            session_cls: type[CMMSSession] = CMMS_SESSION_MAP[cmms_name]
            session = session_cls(
                base_url=cmms_permission.cmms_integration.domain_name,
            )

            session.authenticate(
                username=secret["username"],
                api_key=secret["api_key"],
            )

            result = session.get_all_tickets(
                project_name=cmms_permission.cmms_integration.project_name,
                start=start,
                end=end,
                device_ids=cmms_device_ids,
            )

            tickets.extend(result)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    # sort items by created_at
    tickets.sort(
        key=lambda x: x.created_at.replace(tzinfo=pytz.UTC)
        if x.created_at
        else datetime.min.replace(tzinfo=pytz.UTC),
        reverse=True,
    )

    return CMMSResponse(
        data=tickets,
        metadata=CMMSMetadata(integration_configured=integration_configured),
    )
