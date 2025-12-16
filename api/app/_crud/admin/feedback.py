from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def create_feedback(
    db: AsyncSession,
    *,
    feedback: models.Feedback,
):
    """todo

    Args:
        db: TODO: describe.
        feedback: TODO: describe.
    """
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback
