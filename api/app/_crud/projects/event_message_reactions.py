import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models


async def get_event_message_reactions(
    *,
    db: AsyncSession,
    event_message_id: int | None = None,
) -> list[models.EventMessageReaction]:
    """Get event message reactions, optionally filtered by event_message_id.

    Args:
        db: TODO: describe.
        event_message_id: TODO: describe.
    """
    stmt = select(models.EventMessageReaction)

    if event_message_id is not None:
        stmt = stmt.where(
            models.EventMessageReaction.event_message_id == event_message_id
        )

    stmt = stmt.order_by(models.EventMessageReaction.created_at.asc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_event_message_reactions_by_event_id(
    *,
    db: AsyncSession,
    event_id: int,
) -> list[models.EventMessageReaction]:
    """Get all event message reactions for a specific event.

    Args:
        db: TODO: describe.
        event_id: TODO: describe.
    """
    stmt = (
        select(models.EventMessageReaction)
        .join(models.EventMessage)
        .where(models.EventMessage.event_id == event_id)
    )

    stmt = stmt.order_by(models.EventMessageReaction.created_at.asc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_event_message_reaction(
    *,
    db: AsyncSession,
    event_message_id: int,
    user_id: str,
    reaction_type: enumerations.ReactionType,
) -> models.EventMessageReaction | None:
    """Get a specific reaction if it exists.

    Args:
        db: TODO: describe.
        event_message_id: TODO: describe.
        user_id: TODO: describe.
        reaction_type: TODO: describe.
    """
    stmt = (
        select(models.EventMessageReaction)
        .where(models.EventMessageReaction.event_message_id == event_message_id)
        .where(models.EventMessageReaction.user_id == user_id)
        .where(models.EventMessageReaction.reaction_type == reaction_type)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_event_message_reaction(
    *,
    db: AsyncSession,
    event_message_id: int,
    user_id: str,
    reaction_type: enumerations.ReactionType,
) -> models.EventMessageReaction:
    """Create a new event message reaction.

    Args:
        db: TODO: describe.
        event_message_id: TODO: describe.
        user_id: TODO: describe.
        reaction_type: TODO: describe.
    """
    now = datetime.datetime.now(datetime.UTC)
    reaction = models.EventMessageReaction(
        event_message_id=event_message_id,
        user_id=user_id,
        reaction_type=reaction_type,
        created_at=now,
    )
    db.add(reaction)
    await db.flush()
    await db.refresh(reaction)
    return reaction


async def delete_event_message_reaction(
    *,
    db: AsyncSession,
    reaction: models.EventMessageReaction,
) -> None:
    """Delete an event message reaction.

    Args:
        db: TODO: describe.
        reaction: TODO: describe.
    """
    await db.delete(reaction)
    await db.flush()
