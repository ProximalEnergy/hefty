from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models
from core.enumerations import UserTypeEnum


async def get_user_type(
    *,
    db: AsyncSession,
    user_type_id: UserTypeEnum,
):
    query = select(models.UserType).filter(models.UserType.user_type_id == user_type_id)
    result = await db.execute(query)
    return result.scalars().first()
