from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def create_feedback(
    db: AsyncSession,
    *,
    feedback: models.Feedback,
):
    """Create a feedback record.

    Args:
        db: Database session.
        feedback: Feedback model to persist.
    """
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback
