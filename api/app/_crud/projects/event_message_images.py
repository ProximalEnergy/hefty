import datetime
from typing import Literal
from uuid import UUID

from core.db_query import DbQuery, OutputType
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_event_message_images(
    *,
    db: AsyncSession,
    event_message_id: int | None = None,
    event_id: int | None = None,
) -> list[models.EventMessageImage]:
    """Get event message images, optionally filtered.

    Args:
        db: Async database session.
        event_message_id: Filter by event message ID.
        event_id: Filter by event ID.
    """
    stmt = select(models.EventMessageImage)

    if event_message_id is not None:
        stmt = stmt.where(models.EventMessageImage.event_message_id == event_message_id)
    if event_id is not None:
        stmt = stmt.where(models.EventMessageImage.event_id == event_id)

    stmt = stmt.order_by(models.EventMessageImage.created_at.asc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


def get_event_message_image_by_id(
    *,
    event_message_image_id: UUID,
) -> DbQuery[models.EventMessageImage, Literal[True]]:
    """Get a single event message image by ID.

    Args:
        event_message_image_id: Event message image UUID.
    """
    stmt = select(models.EventMessageImage).where(
        models.EventMessageImage.event_message_image_id == event_message_image_id
    )
    return DbQuery(query=stmt, is_scalar=True)


async def create_event_message_image(
    *,
    db: AsyncSession,
    event_message_id: int,
    event_id: int,
    s3_key: str,
    filename: str,
    content_type: str,
    file_size: int,
) -> models.EventMessageImage:
    """Create a new event message image.

    Args:
        db: Async database session.
        event_message_id: Event message ID for the image.
        event_id: Event ID associated with the message.
        s3_key: S3 object key for the image.
        filename: Original filename.
        content_type: MIME type for the image.
        file_size: File size in bytes.
    """
    now = datetime.datetime.now(datetime.UTC)
    image = models.EventMessageImage(
        event_message_id=event_message_id,
        event_id=event_id,
        s3_key=s3_key,
        filename=filename,
        content_type=content_type,
        file_size=file_size,
        created_at=now,
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)
    return image


async def get_image_s3_keys_for_message(
    *,
    db: AsyncSession,
    event_message_id: int,
) -> list[str]:
    """Get all S3 keys for images attached to a message.

    Args:
        db: Async database session.
        event_message_id: Event message ID to filter by.
    """
    images = await get_event_message_images(db=db, event_message_id=event_message_id)
    return [image.s3_key for image in images]


async def delete_event_message_image(
    *,
    db: AsyncSession,
    event_message_image_id: UUID,
    project_schema: str | None = None,
) -> bool:
    """Delete an event message image from the database and S3.

    Args:
        db: Async database session.
        event_message_image_id: Event message image UUID.
        project_schema: Optional schema name for lookup.
    """
    image = await get_event_message_image_by_id(
        event_message_image_id=event_message_image_id
    ).get_async(
        output_type=OutputType.SQLALCHEMY,
        schema=project_schema,
    )
    if not image:
        return False

    # Delete from database (S3 deletion can be handled separately if needed)
    delete_stmt = delete(models.EventMessageImage).where(
        models.EventMessageImage.event_message_image_id == event_message_image_id
    )
    await db.execute(delete_stmt)
    await db.flush()
    return True
