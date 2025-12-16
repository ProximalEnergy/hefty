import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from core.models import DroneIntegration
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces import DroneIntegrationCreate, DroneIntegrationUpdate


async def get_drone_integrations(*, db: AsyncSession) -> Sequence[DroneIntegration]:
    """Get all drone integrations.

    Args:
        db: TODO: describe.
    """
    stmt = sa.select(DroneIntegration)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_drone_integration_by_project_id(
    *, db: AsyncSession, project_id: uuid.UUID
) -> DroneIntegration | None:
    """Get the first drone integration for a given project.

    Args:
        db: TODO: describe.
        project_id: TODO: describe.
    """
    stmt = sa.select(DroneIntegration).where(DroneIntegration.project_id == project_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def create_drone_integration(
    *, db: AsyncSession, drone_integration: DroneIntegrationCreate
) -> DroneIntegration:
    """Create a new drone integration.

    Args:
        db: TODO: describe.
        drone_integration: TODO: describe.
    """
    db_drone_integration = DroneIntegration(**drone_integration.model_dump())
    db.add(db_drone_integration)
    await db.commit()
    await db.refresh(db_drone_integration)
    return db_drone_integration


async def update_drone_integration(
    *,
    db: AsyncSession,
    drone_integration_id: int,
    drone_integration: DroneIntegrationUpdate,
) -> DroneIntegration | None:
    """Update a drone integration.

    Args:
        db: TODO: describe.
        drone_integration_id: TODO: describe.
        drone_integration: TODO: describe.
    """
    db_drone_integration = await db.get(DroneIntegration, drone_integration_id)
    if db_drone_integration:
        db_drone_integration.project_id = drone_integration.project_id
        db_drone_integration.drone_provider_id = drone_integration.drone_provider_id
        db_drone_integration.provider_project_id = drone_integration.provider_project_id
        await db.commit()
        await db.refresh(db_drone_integration)
    return db_drone_integration


async def delete_drone_integration(
    *, db: AsyncSession, drone_integration_id: int
) -> None:
    """Delete a drone integration.

    Args:
        db: TODO: describe.
        drone_integration_id: TODO: describe.
    """
    db_drone_integration = await db.get(DroneIntegration, drone_integration_id)
    if db_drone_integration:
        await db.delete(db_drone_integration)
        await db.commit()
