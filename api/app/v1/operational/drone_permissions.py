import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.operational.drone_permissions import (
    create_drone_permission,
    delete_drone_permission,
    get_drone_permissions,
    update_drone_permission,
)
from app.dependencies import get_async_db, requires_superadmin_async
from app.interfaces import (
    DronePermissionCreate,
    DronePermissionInterface,
    DronePermissionUpdate,
)

router = APIRouter(prefix="/drone-permissions")


@router.get("", response_model=list[DronePermissionInterface])
async def get_drone_permissions_(
    db: AsyncSession = Depends(get_async_db),
):
    """Retrieve all drone permissions.

    Args:
        db: Description for db.
    """
    return await get_drone_permissions(db=db)


@router.post(
    "",
    response_model=DronePermissionInterface,
    dependencies=[Depends(requires_superadmin_async)],
)
async def create_drone_permission_(
    drone_permission: DronePermissionCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new drone permission.

    Args:
        drone_permission: Description for drone_permission.
        db: Description for db.
    """
    return await create_drone_permission(db=db, drone_permission=drone_permission)


@router.put(
    "/{drone_integration_id}/{company_id}",
    response_model=DronePermissionInterface,
    dependencies=[Depends(requires_superadmin_async)],
)
async def update_drone_permission_(
    drone_integration_id: int,
    company_id: uuid.UUID,
    drone_permission: DronePermissionUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """Update a drone permission.

    Args:
        drone_integration_id: Description for drone_integration_id.
        company_id: Description for company_id.
        drone_permission: Description for drone_permission.
        db: Description for db.
    """
    return await update_drone_permission(
        db=db,
        drone_integration_id=drone_integration_id,
        company_id=company_id,
        drone_permission=drone_permission,
    )


@router.delete(
    "/{drone_integration_id}/{company_id}",
    dependencies=[Depends(requires_superadmin_async)],
)
async def delete_drone_permission_(
    drone_integration_id: int,
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a drone permission.

    Args:
        drone_integration_id: Description for drone_integration_id.
        company_id: Description for company_id.
        db: Description for db.
    """
    await delete_drone_permission(
        db=db,
        drone_integration_id=drone_integration_id,
        company_id=company_id,
    )
    return HTTPException(status_code=200, detail="Drone permission deleted")
