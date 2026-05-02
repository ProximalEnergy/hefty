import datetime
from typing import Annotated, Any, cast

import core.models as models
from core.crud.project import event_cmms_tickets as crud_event_cmms_tickets
from core.crud.project import events as crud_events
from core.db_query import OutputType
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces, utils
from app._dependencies.authentication import get_user
from app.dependencies import get_project_api, get_project_db_async
from app.interfaces import UserAuthed

router = APIRouter(
    prefix="/event-cmms-tickets",
    tags=["event-cmms-tickets"],
    include_in_schema=utils.get_include_in_schema(),
)


class _CreateEventCMMSTicketRequest(BaseModel):
    event_id: int
    cmms_ticket_id: int


class _EventIdsLookupBody(BaseModel):
    """Large event-id lists belong in the body, not repeated query params."""

    event_ids: list[int]


class _EventWithScore(interfaces.EventInterface):
    score: int


class _TicketWithScore(interfaces.CMMSTicketInterface):
    score: int


@router.get("", response_model=list[interfaces.EventCMMSTicketInterface])
async def get_event_cmms_tickets_route(
    *,
    project: models.Project = Depends(get_project_api),
    event_cmms_ticket_ids: Annotated[list[int] | None, Query()] = None,
    event_ids: Annotated[list[int] | None, Query()] = None,
    cmms_ticket_ids: Annotated[list[int] | None, Query()] = None,
    created_by_user_ids: Annotated[list[str] | None, Query()] = None,
    created_at_gte: Annotated[datetime.datetime | None, Query()] = None,
    created_at_lte: Annotated[datetime.datetime | None, Query()] = None,
):
    """Get event-CMMS ticket relationships by various filters.

    Args:
        project: The project to get the event-CMMS ticket relationships for.
        event_cmms_ticket_ids: The event-CMMS ticket ids to get the relationships for.
        event_ids: The event ids to get the relationships for.
        cmms_ticket_ids: The CMMS ticket ids to get the relationships for.
        created_by_user_ids: The user ids to get the relationships for.
        created_at_gte: The created at greater than or equal to.
        created_at_lte: The created at less than or equal to.
    """
    event_cmms_tickets_query = crud_event_cmms_tickets.get_event_cmms_tickets(
        event_cmms_ticket_ids=event_cmms_ticket_ids,
        event_ids=event_ids,
        cmms_ticket_ids=cmms_ticket_ids,
        created_by_user_ids=created_by_user_ids,
        created_at_gte=created_at_gte,
        created_at_lte=created_at_lte,
    )
    event_cmms_tickets = await event_cmms_tickets_query.get_async(
        schema=project.name_short, output_type=OutputType.PANDAS
    )
    records = cast(list[dict[str, Any]], event_cmms_tickets.to_dict(orient="records"))
    event_cmms_tickets_models = [models.EventCMMSTicket(**record) for record in records]
    return event_cmms_tickets_models


@router.post("/by-event-ids", response_model=list[interfaces.EventCMMSTicketInterface])
async def lookup_event_cmms_tickets_by_event_ids(
    *,
    project: models.Project = Depends(get_project_api),
    body: _EventIdsLookupBody,
):
    """Return event–CMMS links for many events (body), avoiding huge GET URLs."""
    unique_ids = list(dict.fromkeys(body.event_ids))
    if not unique_ids:
        return []
    event_cmms_tickets_query = crud_event_cmms_tickets.get_event_cmms_tickets(
        event_ids=unique_ids,
    )
    event_cmms_tickets = await event_cmms_tickets_query.get_async(
        schema=project.name_short, output_type=OutputType.PANDAS
    )
    records = cast(list[dict[str, Any]], event_cmms_tickets.to_dict(orient="records"))
    return [models.EventCMMSTicket(**record) for record in records]


@router.post("", response_model=interfaces.EventCMMSTicketInterface)
async def create_event_cmms_ticket(
    *,
    project_db: AsyncSession = Depends(get_project_db_async),
    user_data: Annotated[UserAuthed, Depends(get_user)],
    request: _CreateEventCMMSTicketRequest = Body(...),
):
    """Create a new event-CMMS ticket relationship.

    Args:
        project_db: The project database session.
        user_data: The user data.
        request: The request body.
    """
    event_cmms_ticket = await crud_event_cmms_tickets.add_event_cmms_ticket(
        db=project_db,
        event_id=request.event_id,
        cmms_ticket_id=request.cmms_ticket_id,
        created_by_user_id=user_data.user_id,
    )
    return event_cmms_ticket


@router.delete(
    "/{event_cmms_ticket_id}", response_model=interfaces.EventCMMSTicketInterface | None
)
async def delete_event_cmms_ticket_route(
    *,
    project_db: AsyncSession = Depends(get_project_db_async),
    event_cmms_ticket_id: int,
):
    """Delete an event-CMMS ticket relationship.

    Args:
        project_db: The project database session.
        event_cmms_ticket_id: The event-CMMS ticket ID.
    """
    event_cmms_ticket = await crud_event_cmms_tickets.delete_event_cmms_ticket(
        db=project_db, event_cmms_ticket_id=event_cmms_ticket_id
    )
    return event_cmms_ticket


@router.get("/suggested-events", response_model=list[_EventWithScore])
async def get_suggested_events_from_ticket(
    *,
    project: models.Project = Depends(get_project_api),
    project_db: AsyncSession = Depends(get_project_db_async),
    cmms_ticket_id: int = Query(...),
    cmms_integration_id: int = Query(...),
    cmms_device_id: str | None = Query(None),
    source_created_at: datetime.datetime | None = Query(None),
):
    """Get suggested events from a ticket."""
    rows = await crud_event_cmms_tickets.get_suggested_events_with_score_from_ticket(
        cmms_ticket_id=cmms_ticket_id,
        cmms_integration_id=cmms_integration_id,
        cmms_device_id=cmms_device_id,
        source_created_at=source_created_at,
        project=project,
        project_db=project_db,
        limit=10,
    )
    if not rows:
        return []

    return [
        _EventWithScore(
            **interfaces.EventInterface.model_validate(ev.__dict__).__dict__,
            score=score,
        )
        for (ev, score) in rows
    ]


@router.get("/suggested-tickets", response_model=list[_TicketWithScore])
async def get_suggested_tickets_from_event(
    *,
    project: models.Project = Depends(get_project_api),
    project_db: AsyncSession = Depends(get_project_db_async),
    event_id: int = Query(...),
    cmms_integration_id: int = Query(...),
):
    """Get suggested CMMS tickets for an event."""
    events = await crud_events.get_events_by_id(
        event_ids=[event_id],
    ).get_async(
        schema=project.name_short,
        output_type=OutputType.SQLALCHEMY,
    )
    if not events:
        raise HTTPException(status_code=404, detail="Event not found")

    rows = await crud_event_cmms_tickets.get_suggested_tickets_with_score_from_event(
        event=events[0],
        cmms_integration_id=cmms_integration_id,
        project=project,
        project_db=project_db,
        limit=10,
    )
    if not rows:
        return []

    return [
        _TicketWithScore(
            **interfaces.CMMSTicketInterface.model_validate(ticket.__dict__).__dict__,
            score=score,
        )
        for (ticket, score) in rows
    ]
