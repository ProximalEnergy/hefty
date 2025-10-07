import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from core.models import DronePermission
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces import DronePermissionCreate, DronePermissionUpdate


async def get_drone_permissions(*, db: AsyncSession) -> Sequence[DronePermission]:
    """Get all drone permissions."""
    stmt = sa.select(DronePermission)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_drone_permission(
    *, db: AsyncSession, drone_permission: DronePermissionCreate
) -> DronePermission:
    """Create a new drone permission."""
    db_drone_permission = DronePermission(**drone_permission.model_dump())
    db.add(db_drone_permission)
    await db.commit()
    await db.refresh(db_drone_permission)
    return db_drone_permission


async def update_drone_permission(
    *,
    db: AsyncSession,
    drone_integration_id: int,
    company_id: uuid.UUID,
    drone_permission: DronePermissionUpdate,
) -> DronePermission | None:
    """Update a drone permission."""
    db_drone_permission = await db.get(
        DronePermission,
        {"drone_integration_id": drone_integration_id, "company_id": company_id},
    )
    if db_drone_permission:
        db_drone_permission.can_view = drone_permission.can_view
        await db.commit()
        await db.refresh(db_drone_permission)
    return db_drone_permission


async def delete_drone_permission(
    *, db: AsyncSession, drone_integration_id: int, company_id: uuid.UUID
) -> None:
    """Delete a drone permission."""
    delete_stmt = delete(DronePermission).where(
        DronePermission.drone_integration_id == drone_integration_id,
        DronePermission.company_id == company_id,
    )
    await db.execute(delete_stmt)
    await db.commit()
