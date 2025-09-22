import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models

logger = logging.getLogger(__name__)


async def update_user_kpi_type_favorite(
    *,
    db: AsyncSession,
    user_id: str,
    kpi_type_id: int,
    is_favorited: bool,
) -> models.UserKPITypes:
    """Update the is_favorited field for a user's kpi_type.
    If the relationship does not exist, it will be created.
    """
    try:
        # Find the existing user kpi_type relationship
        query = select(models.UserKPITypes).where(
            models.UserKPITypes.user_id == user_id,
            models.UserKPITypes.kpi_type_id == kpi_type_id,
        )
        result = await db.execute(query)
        user_kpi_type = result.scalar_one_or_none()

        if not user_kpi_type:
            # Create new relationship if it doesn't exist
            user_kpi_type = models.UserKPITypes(
                user_id=user_id,
                kpi_type_id=kpi_type_id,
                is_favorited=is_favorited,
            )
            db.add(user_kpi_type)
            logger.info(
                f"Creating new favorite status for user {user_id}, "
                f"kpi_type {kpi_type_id} to {is_favorited}"
            )
        else:
            # Update the is_favorited field
            user_kpi_type.is_favorited = is_favorited
            logger.info(
                f"Successfully updated favorite status for user "
                f"{user_id}, kpi_type {kpi_type_id} to {is_favorited}"
            )

        await db.commit()
        await db.refresh(user_kpi_type)

        return user_kpi_type

    except Exception as e:
        logger.error(
            f"Failed to update favorite status for user "
            f"{user_id}, kpi_type {kpi_type_id}: {e}"
        )
        await db.rollback()
        raise


async def get_user_favorited_kpi_types(
    *,
    db: AsyncSession,
    user_id: str,
) -> list[models.UserKPITypes]:
    """Get all favorited KPI types for a given user.

    Args:
        db: Database session
        user_id: The user ID to get favorited KPI types for

    Returns:
        List of UserKPITypes records where is_favorited is True
    """
    try:
        query = select(models.UserKPITypes).where(
            models.UserKPITypes.user_id == user_id,
            models.UserKPITypes.is_favorited == True,
        )
        result = await db.execute(query)
        favorited_kpi_types = result.scalars().all()

        logger.info(
            f"Retrieved {len(favorited_kpi_types)} favorited KPI types "
            f"for user {user_id}"
        )

        return list(favorited_kpi_types)

    except Exception as e:
        logger.error(f"Failed to get favorited KPI types for user {user_id}: {e}")
        raise
