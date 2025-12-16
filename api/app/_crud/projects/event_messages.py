import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core import models

if TYPE_CHECKING:
    pass


async def get_event_messages(
    *,
    db: AsyncSession,
    event_id: int | None = None,
) -> list[models.EventMessage]:
    """Get event messages, optionally filtered by event_id.
        Includes all messages (both deleted and non-deleted) so deleted messages
        can be displayed with "This message was deleted." text.
        Loads images relationship.

    Args:
        db: TODO: describe.
        event_id: TODO: describe.
    """
    # Get all messages (including deleted ones)
    stmt = select(models.EventMessage).options(selectinload(models.EventMessage.images))

    if event_id is not None:
        stmt = stmt.where(models.EventMessage.event_id == event_id)

    stmt = stmt.order_by(models.EventMessage.created_at.asc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_event_message_by_id(
    *,
    db: AsyncSession,
    event_message_id: int,
) -> models.EventMessage | None:
    """Get a single event message by ID.
        Loads images relationship.

    Args:
        db: TODO: describe.
        event_message_id: TODO: describe.
    """
    stmt = (
        select(models.EventMessage)
        .options(selectinload(models.EventMessage.images))
        .where(models.EventMessage.event_message_id == event_message_id)
        .where(models.EventMessage.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_event_message(
    *,
    db: AsyncSession,
    event_id: int,
    user_id: str,
    body: str,
    mentions: str | None = None,
    parent_message_id: int | None = None,
    private: bool = False,
) -> models.EventMessage:
    """Create a new event message.

    Args:
        db: TODO: describe.
        event_id: TODO: describe.
        user_id: TODO: describe.
        body: TODO: describe.
        mentions: TODO: describe.
        parent_message_id: TODO: describe.
        private: TODO: describe.
    """
    now = datetime.datetime.now(datetime.UTC)
    event_message = models.EventMessage(
        event_id=event_id,
        user_id=user_id,
        body=body,
        mentions=mentions,
        parent_message_id=parent_message_id,
        created_at=now,
        private=private,
    )
    db.add(event_message)
    await db.flush()
    await db.refresh(event_message)
    return event_message


async def update_event_message(
    *,
    db: AsyncSession,
    event_message_id: int,
    body: str,
    mentions: str | None = None,
) -> models.EventMessage | None:
    """Update an event message body and mentions, set edited_at timestamp.

    Args:
        db: TODO: describe.
        event_message_id: TODO: describe.
        body: TODO: describe.
        mentions: TODO: describe.
    """
    event_message = await get_event_message_by_id(
        db=db, event_message_id=event_message_id
    )
    if not event_message:
        return None

    event_message.body = body
    event_message.mentions = mentions
    event_message.edited_at = datetime.datetime.now(datetime.UTC)
    await db.flush()
    await db.refresh(event_message)
    return event_message


async def update_event_message_image_s3_keys(
    *,
    db: AsyncSession,
    event_message_id: int,
    image_s3_keys: str | None,
) -> models.EventMessage | None:
    """Update the image_s3_keys field for an event message.

    Args:
        db: TODO: describe.
        event_message_id: TODO: describe.
        image_s3_keys: TODO: describe.
    """
    event_message = await get_event_message_by_id(
        db=db, event_message_id=event_message_id
    )
    if not event_message:
        return None

    event_message.image_s3_keys = image_s3_keys
    await db.flush()
    await db.refresh(event_message)
    return event_message


async def get_users_who_posted_to_event(
    *,
    db: AsyncSession,
    event_id: int,
) -> set[str]:
    """Get all user_ids who have posted messages to an event.

    Args:
        db: TODO: describe.
        event_id: TODO: describe.
    """
    stmt = (
        select(models.EventMessage.user_id)
        .where(models.EventMessage.event_id == event_id)
        .where(models.EventMessage.deleted_at.is_(None))
        .distinct()
    )
    result = await db.execute(stmt)
    return set(result.scalars().all())


async def get_all_mentioned_users_for_event(
    *,
    db: AsyncSession,
    event_id: int,
) -> set[str]:
    """Get all unique usernames mentioned in messages for an event.

    Args:
        db: TODO: describe.
        event_id: TODO: describe.
    """
    messages = await get_event_messages(db=db, event_id=event_id)
    mentioned_users = set()

    for message in messages:
        if message.mentions:
            usernames = [u.strip() for u in message.mentions.split(",")]
            mentioned_users.update(usernames)

    return mentioned_users


async def delete_event_message(
    *,
    db: AsyncSession,
    event_message_id: int,
    user_id: str,
) -> models.EventMessage | None:
    """Soft delete an event message by setting deleted_at timestamp.
        Validates that the user owns the message.

    Args:
        db: TODO: describe.
        event_message_id: TODO: describe.
        user_id: TODO: describe.
    """
    # Get message without deleted_at filter to allow checking ownership
    stmt = (
        select(models.EventMessage)
        .options(selectinload(models.EventMessage.images))
        .where(models.EventMessage.event_message_id == event_message_id)
    )
    result = await db.execute(stmt)
    event_message = result.scalar_one_or_none()

    if not event_message:
        return None

    # Verify user owns the message
    if event_message.user_id != user_id:
        return None

    # Soft delete by setting deleted_at
    event_message.deleted_at = datetime.datetime.now(datetime.UTC)
    await db.flush()
    await db.refresh(event_message)
    return event_message
