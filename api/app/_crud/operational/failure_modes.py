from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def update_event_failure_mode(
    *,
    db: AsyncSession,
    event_id: int,
    failure_mode_id: int,
):
    """Assign a failure mode to an event and persist the change.

    Args:
        db: Operational database session used for fetching and updating the
            event record.
        event_id: Identifier of the event being updated.
        failure_mode_id: Failure mode to associate with the event.
    """
    query = select(models.Event).where(models.Event.event_id == event_id)
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    if event:
        event.failure_mode_id = failure_mode_id
        await db.commit()
        await db.refresh(event)
    return event


async def get_root_causes(
    *,
    db: AsyncSession,
    root_cause_ids: list[int] = [],
    device_type_ids: list[int] = [],
):
    """Fetch root causes filtered by IDs or device types.

    Args:
        db: Operational database session for retrieving root causes.
        root_cause_ids: Root cause identifiers to match; returns all when
            omitted.
        device_type_ids: Device type IDs to filter associated root causes.
    """
    query = select(models.RootCause)
    if root_cause_ids:
        query = query.where(models.RootCause.root_cause_id.in_(root_cause_ids))
    if device_type_ids:
        query = query.where(models.RootCause.device_type_id.in_(device_type_ids))
    result = await db.execute(query)
    return result.scalars().all()


async def update_event_root_cause(
    *,
    db: AsyncSession,
    event_id: int,
    root_cause_id: int | None,
):
    """Update an event with a new root cause reference.

    Args:
        db: Operational database session used to read and modify the event.
        event_id: Identifier of the event whose root cause is being changed.
        root_cause_id: Root cause identifier to set on the event, or ``None`` to
            clear it.
    """
    query = select(models.Event).where(models.Event.event_id == event_id)
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    if event:
        event.root_cause_id = root_cause_id
        await db.commit()
        await db.refresh(event)
    return event
