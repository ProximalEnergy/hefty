from collections.abc import Sequence

import sqlalchemy as sa
from core.models import DroneProvider
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces import DroneProviderCreate, DroneProviderUpdate


async def get_drone_providers(*, db: AsyncSession) -> Sequence[DroneProvider]:
    """Get all drone providers.

    Args:
        db: TODO: describe.
    """
    stmt = sa.select(DroneProvider)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_drone_provider(
    *, db: AsyncSession, drone_provider: DroneProviderCreate
) -> DroneProvider:
    """Create a new drone provider.

    Args:
        db: TODO: describe.
        drone_provider: TODO: describe.
    """
    db_drone_provider = DroneProvider(**drone_provider.model_dump())
    db.add(db_drone_provider)
    await db.commit()
    await db.refresh(db_drone_provider)
    return db_drone_provider


async def update_drone_provider(
    *, db: AsyncSession, drone_provider_id: int, drone_provider: DroneProviderUpdate
) -> DroneProvider | None:
    """Update a drone provider.

    Args:
        db: TODO: describe.
        drone_provider_id: TODO: describe.
        drone_provider: TODO: describe.
    """
    db_drone_provider = await db.get(DroneProvider, drone_provider_id)
    if db_drone_provider:
        db_drone_provider.name_short = drone_provider.name_short
        db_drone_provider.name_long = drone_provider.name_long
        await db.commit()
        await db.refresh(db_drone_provider)
    return db_drone_provider


async def delete_drone_provider(*, db: AsyncSession, drone_provider_id: int) -> None:
    """Delete a drone provider.

    Args:
        db: TODO: describe.
        drone_provider_id: TODO: describe.
    """
    delete_stmt = delete(DroneProvider).where(
        DroneProvider.drone_provider_id == drone_provider_id
    )
    await db.execute(delete_stmt)
    await db.commit()
