from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def create_feedback(
    db: AsyncSession,
    *,
    feedback: models.Feedback,
):
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback
