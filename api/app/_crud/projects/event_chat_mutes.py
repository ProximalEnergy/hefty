import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_event_chat_mutes(
    *,
    db: AsyncSession,
    event_id: int | None = None,
    user_id: str | None = None,
) -> list[models.EventChatMute]:
    """Get event chat mutes, optionally filtered."""
    stmt = select(models.EventChatMute)

    if event_id is not None:
        stmt = stmt.where(models.EventChatMute.event_id == event_id)
    if user_id is not None:
        stmt = stmt.where(models.EventChatMute.user_id == user_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def is_event_chat_muted(
    *,
    db: AsyncSession,
    event_id: int,
    user_id: str,
) -> bool:
    """Check if a user has muted an event chat."""
    stmt = (
        select(models.EventChatMute)
        .where(models.EventChatMute.event_id == event_id)
        .where(models.EventChatMute.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def toggle_event_chat_mute(
    *,
    db: AsyncSession,
    event_id: int,
    user_id: str,
) -> bool:
    """Toggle mute status for an event chat.
    Returns True if muted, False if unmuted.
    """
    existing = await get_event_chat_mutes(db=db, event_id=event_id, user_id=user_id)

    if existing:
        # Unmute: delete the mute record
        for mute in existing:
            await db.delete(mute)
        await db.flush()
        return False
    else:
        # Mute: create a new mute record
        now = datetime.datetime.now(datetime.UTC)
        mute = models.EventChatMute(
            event_id=event_id,
            user_id=user_id,
            muted_at=now,
        )
        db.add(mute)
        await db.flush()
        return True
