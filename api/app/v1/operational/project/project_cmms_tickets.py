from datetime import datetime
from typing import Annotated
from uuid import UUID

import pytz
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.operational.cmms_permissions import get_cmms_permissions_by_project_id
from core import models

router = APIRouter(
    prefix="/cmms-tickets",
    tags=["cmms-tickets"],
)


class CMMSTicket(BaseModel):
    """A CMMS ticket with provider metadata and scheduling details."""

    cmms_ticket_id: int  # internal ticket_id from Proximal's DB.
    cmms_provider: str
    id: int  # machine readable identifier
    key: str  # human readable identifier
    cmms_integration_id: int
    created_at: datetime | None = None  # the date and time the ticket was created
    due_date: datetime | None = None
    summary: str | None = None
    summary_long: str | None = None
    status: str | None = None
    status_change_at: datetime | None = None
    priority: str | None = None
    reporter: str | None = None
    assigned_to: str | None = None
    location: str | None = None
    cmms_device_id: str | None = None  # according to the CMMS provider
    cmms_device_name: str | None = None  # according to the CMMS provider
    link: str | None = None  # the link to the ticket on the CMMS provider's platform


class CMMSMetadata(BaseModel):
    """Metadata about CMMS integration availability for the project."""

    integration_configured: bool


class CMMSResponse(BaseModel):
    """Response wrapper containing integration state and ticket results."""

    metadata: CMMSMetadata
    data: list[CMMSTicket]


@router.get("", response_model=CMMSResponse)
async def get_cmms_tickets(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project_db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],  # will be needed when incorperating device data
    user: Annotated[interfaces.UserData, Depends(dependencies.get_user_data_async)],
    device_ids: Annotated[list[int] | None, Query()] = None,
    device_type_ids: Annotated[list[int] | None, Query()] = None,
):
    """Pulls the first 50 tickets for each CMMS provider.

        Parameters:
        -----------
        project_id : UUID
            The project identifier
        db : AsyncSession
            Database session
        project_db : AsyncSession
            Project database session
        user : interfaces.UserData
            To get the company id
        device_ids : Optional[List[int]]
            The list of device ids to filter the tickets by
        device_type_ids : Optional[List[int]]
            The list of device type ids to filter the tickets by

    Args:
        project_id: Operational project identifier for scoping CMMS data.
        db: Primary application database session used for permissions lookup.
        project_db: Project-level async session for ticket and device queries.
        user: Authenticated user context containing company membership.
        start: Optional ISO date string to filter tickets created after this time.
        end: Optional ISO date string limiting tickets created before this time.
        device_ids: Optional list of project device IDs to filter matching tickets.
        device_type_ids: Optional list of device type IDs to filter matching tickets.
    """
    # First get integrations to see if there are any configured

    cmms_permissions = await get_cmms_permissions_by_project_id(
        db=db,
        company_id=user.company_id,
        project_id=project_id,
        can_view=True,
    )

    # If there are any configured integrations, then the integration is
    # considered configured
    integration_configured = len(cmms_permissions) > 0

    cmms_integration_ids = [
        cmms_permission.cmms_integration.cmms_integration_id
        for cmms_permission in cmms_permissions
    ]

    stmt = (
        select(
            models.CMMSTicket,
            models.CMMSProvider.name_long,
        )
        .join(
            models.CMMSIntegration,
            models.CMMSIntegration.cmms_integration_id
            == models.CMMSTicket.cmms_integration_id,
        )
        .join(
            models.CMMSProvider,
            models.CMMSProvider.cmms_provider_id
            == models.CMMSIntegration.cmms_provider_id,
        )
        .where(models.CMMSTicket.cmms_integration_id.in_(cmms_integration_ids))
    )

    if device_ids is not None:
        stmt = stmt.where(
            exists().where(
                and_(
                    models.CMMSDevice.cmms_device_id
                    == models.CMMSTicket.cmms_device_id,
                    models.CMMSDevice.cmms_integration_id
                    == models.CMMSTicket.cmms_integration_id,
                    models.CMMSDevice.device_id.in_(device_ids),
                )
            )
        )
    elif device_type_ids is not None:
        stmt = stmt.where(
            exists().where(
                and_(
                    models.CMMSDevice.cmms_device_id
                    == models.CMMSTicket.cmms_device_id,
                    models.CMMSDevice.cmms_integration_id
                    == models.CMMSTicket.cmms_integration_id,
                    models.CMMSDevice.device.has(
                        models.Device.device_type_id.in_(device_type_ids)
                    ),
                )
            )
        )

    result = await project_db.execute(stmt)
    queried_tickets = result.all()

    tickets = [
        CMMSTicket(
            cmms_ticket_id=ticket[0].cmms_ticket_id,
            cmms_provider=ticket[1],
            cmms_integration_id=ticket[0].cmms_integration_id,
            id=ticket[0].source_id,
            key=ticket[0].key,
            created_at=ticket[0].source_created_at,
            due_date=ticket[0].due_date,
            summary=ticket[0].summary,
            status=ticket[0].status,
            status_change_at=ticket[0].status_change_at,
            priority=ticket[0].priority,
            reporter=ticket[0].reporter,
            assigned_to=ticket[0].assigned_to,
            location=ticket[0].location,
            cmms_device_id=ticket[0].cmms_device_id,
            cmms_device_name=ticket[0].cmms_device_name,
            link=ticket[0].link,
        )
        for ticket in queried_tickets
    ]

    # sort items by created_at
    tickets.sort(
        key=lambda x: (
            x.created_at.replace(tzinfo=pytz.UTC)
            if x.created_at
            else datetime.min.replace(tzinfo=pytz.UTC)
        ),
        reverse=True,
    )

    return CMMSResponse(
        data=tickets,
        metadata=CMMSMetadata(integration_configured=integration_configured),
    )
