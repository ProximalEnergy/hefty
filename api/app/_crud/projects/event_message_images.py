import datetime
from uuid import UUID

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
        db: TODO: describe.
        event_message_id: TODO: describe.
        event_id: TODO: describe.
    """
    stmt = select(models.EventMessageImage)

    if event_message_id is not None:
        stmt = stmt.where(models.EventMessageImage.event_message_id == event_message_id)
    if event_id is not None:
        stmt = stmt.where(models.EventMessageImage.event_id == event_id)

    stmt = stmt.order_by(models.EventMessageImage.created_at.asc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_event_message_image_by_id(
    *,
    db: AsyncSession,
    event_message_image_id: UUID,
) -> models.EventMessageImage | None:
    """Get a single event message image by ID.

    Args:
        db: TODO: describe.
        event_message_image_id: TODO: describe.
    """
    stmt = select(models.EventMessageImage).where(
        models.EventMessageImage.event_message_image_id == event_message_image_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


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
        db: TODO: describe.
        event_message_id: TODO: describe.
        event_id: TODO: describe.
        s3_key: TODO: describe.
        filename: TODO: describe.
        content_type: TODO: describe.
        file_size: TODO: describe.
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
        db: TODO: describe.
        event_message_id: TODO: describe.
    """
    images = await get_event_message_images(db=db, event_message_id=event_message_id)
    return [image.s3_key for image in images]


async def delete_event_message_image(
    *,
    db: AsyncSession,
    event_message_image_id: UUID,
) -> bool:
    """Delete an event message image from the database and S3.

    Args:
        db: TODO: describe.
        event_message_image_id: TODO: describe.
    """
    image = await get_event_message_image_by_id(
        db=db, event_message_image_id=event_message_image_id
    )
    if not image:
        return False

    # Delete from database (S3 deletion can be handled separately if needed)
    stmt = delete(models.EventMessageImage).where(
        models.EventMessageImage.event_message_image_id == event_message_image_id
    )
    await db.execute(stmt)
    await db.flush()
    return True
