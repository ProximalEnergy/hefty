from datetime import datetime
from typing import Annotated, Any, cast
from uuid import UUID

import pandas as pd
import pytz
from core.crud.operational.cmms_permissions import (
    get_cmms_permissions_by_project_id as core_get_cmms_permissions_by_project_id,
)
from core.crud.project.cmms_tickets import get_project_cmms_tickets
from core.db_query import OutputType
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.operational.cmms_permissions import get_cmms_permissions_by_project_id
from app._dependencies.authentication import get_user
from app.interfaces import UserAuthed
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


@router.get("", response_model=CMMSResponse, deprecated=True)
async def get_cmms_tickets(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project_db: Annotated[
        AsyncSession,
        Depends(dependencies.get_project_db_async),
    ],  # will be needed when incorperating device data
    user: Annotated[UserAuthed, Depends(get_user)],
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
        user : UserAuthed
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


class EnrichedCMMSTicket(interfaces.CMMSTicket):
    """An enriched CMMS ticket with provider metadata."""

    cmms_provider_name_long: str


class CMMSTicketV2(BaseModel):
    """Response wrapper containing integration state and ticket results."""

    integration_configured: bool
    data: list[EnrichedCMMSTicket]


@router.get("/v2", response_model=CMMSTicketV2)
async def get_cmms_tickets_v2(
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    user: Annotated[UserAuthed, Depends(get_user)],
    cmms_ticket_ids: Annotated[list[int] | None, Query()] = None,
    cmms_integration_ids: Annotated[list[int] | None, Query()] = None,
    max_results: Annotated[int | None, Query()] = 50,
    device_ids: Annotated[list[int] | None, Query()] = None,
    device_type_ids: Annotated[list[int] | None, Query()] = None,
    source_created_at_start: Annotated[datetime | None, Query()] = None,
    source_created_at_end: Annotated[datetime | None, Query()] = None,
    source_created_order_asc: Annotated[bool, Query()] = False,
    include_json_raw: Annotated[
        bool, Query()
    ] = False,  # include the raw JSON data in the response
):
    """Get the CMMS tickets for a project.

    Args:
        project: The project to get the CMMS tickets for.
        user: The user to get the CMMS tickets for.
        cmms_ticket_ids: The list of CMMS ticket ids to filter by.
        cmms_integration_ids: The list of CMMS integration ids to filter by.
        max_results: The maximum number of tickets to return.
        device_ids: The list of device ids to filter by.
        device_type_ids: The list of device type ids to filter by.
        source_created_at_start: Inclusive lower bound on source_created_at.
        source_created_at_end: Inclusive upper bound on source_created_at.
        source_created_order_asc: Sort by creation time ascending when True.
        include_json_raw: Whether to include the raw JSON data in the response.
    """
    cmms_permissions = await core_get_cmms_permissions_by_project_id(
        company_id=user.company_id,
        project_id=project.project_id,
        can_view=True,
    ).get_async(output_type=OutputType.PANDAS)

    # Early return if no permissions are found
    if cmms_permissions.empty:
        return CMMSTicketV2(
            integration_configured=False,
            data=[],
        )

    cmms_integration_ids = cmms_permissions["cmms_integration_id"].unique().tolist()

    cmms_tickets = await get_project_cmms_tickets(
        cmms_ticket_ids=cmms_ticket_ids,
        cmms_integration_ids=cmms_integration_ids,
        device_ids=device_ids,
        device_type_ids=device_type_ids,
        source_created_at_start=source_created_at_start,
        source_created_at_end=source_created_at_end,
        max_results=max_results,
        include_json_raw=include_json_raw,
        source_created_order_asc=source_created_order_asc,
    ).get_async(schema=project.name_short, output_type=OutputType.PANDAS)

    provider_info = cmms_permissions[
        ["cmms_integration_id", "cmms_provider_name_long"]
    ].drop_duplicates()
    enriched_tickets_df = cmms_tickets.merge(
        provider_info, on="cmms_integration_id", how="left"
    )
    enriched_cmms_tickets: list[EnrichedCMMSTicket] = []
    for ticket_dict in cast(
        list[dict[str, Any]],
        enriched_tickets_df.to_dict(orient="records"),
    ):
        sanitized_ticket = {
            key: (None if pd.isna(value) else value)
            for key, value in ticket_dict.items()
        }
        enriched_cmms_tickets.append(
            EnrichedCMMSTicket.model_validate(sanitized_ticket)
        )

    return CMMSTicketV2(
        integration_configured=True,
        data=enriched_cmms_tickets,
    )
