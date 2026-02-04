import datetime
from typing import Literal

from core.db_query import DbQuery
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
        db: Async database session connected to the operational store.
        event_message_id: Optional message identifier to filter reactions for.
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
        db: Async database session connected to the operational store.
        event_id: Event identifier used to scope associated message reactions.
    """
    stmt = (
        select(models.EventMessageReaction)
        .join(models.EventMessage)
        .where(models.EventMessage.event_id == event_id)
    )

    stmt = stmt.order_by(models.EventMessageReaction.created_at.asc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


def get_event_message_reaction(
    *,
    event_message_id: int,
    user_id: str,
    reaction_type: enumerations.ReactionType,
) -> DbQuery[models.EventMessageReaction, Literal[True]]:
    """Get a specific reaction if it exists.

    Args:
        event_message_id: Message identifier for the reaction being queried.
        user_id: Unique identifier of the reacting user.
        reaction_type: Specific reaction enum to match (e.g., like, dislike).
    """
    stmt = (
        select(models.EventMessageReaction)
        .where(models.EventMessageReaction.event_message_id == event_message_id)
        .where(models.EventMessageReaction.user_id == user_id)
        .where(models.EventMessageReaction.reaction_type == reaction_type)
    )
    return DbQuery(query=stmt, is_scalar=True)


async def create_event_message_reaction(
    *,
    db: AsyncSession,
    event_message_id: int,
    user_id: str,
    reaction_type: enumerations.ReactionType,
) -> models.EventMessageReaction:
    """Create a new event message reaction.

    Args:
        db: Async database session connected to the operational store.
        event_message_id: Message identifier the reaction belongs to.
        user_id: Unique identifier of the reacting user.
        reaction_type: Enum value describing the reaction being added.
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
        db: Async database session connected to the operational store.
        reaction: Reaction model instance to remove from the database.
    """
    await db.delete(reaction)
    await db.flush()
