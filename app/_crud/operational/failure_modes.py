from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_failure_modes(
    *,
    db: AsyncSession,
    failure_mode_ids: list[int] = [],
):
    query = select(models.FailureMode)
    if failure_mode_ids:
        query = query.filter(models.FailureMode.failure_mode_id.in_(failure_mode_ids))
    result = await db.execute(query)
    return result.scalars().all()


async def update_event_failure_mode(
    *,
    db: AsyncSession,
    event_id: int,
    failure_mode_id: int,
):
    query = select(models.Event).filter(models.Event.event_id == event_id)
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
    query = select(models.RootCause)
    if root_cause_ids:
        query = query.filter(models.RootCause.root_cause_id.in_(root_cause_ids))
    if device_type_ids:
        query = query.filter(models.RootCause.device_type_id.in_(device_type_ids))
    result = await db.execute(query)
    return result.scalars().all()


async def update_event_root_cause(
    *,
    db: AsyncSession,
    event_id: int,
    root_cause_id: int | None,
):
    query = select(models.Event).filter(models.Event.event_id == event_id)
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    if event:
        event.root_cause_id = root_cause_id
        await db.commit()
        await db.refresh(event)
    return event
