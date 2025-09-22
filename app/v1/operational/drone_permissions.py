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
from app.interfaces import DronePermission, DronePermissionCreate, DronePermissionUpdate

router = APIRouter(prefix="/drone-permissions")


@router.get("", response_model=list[DronePermission])
async def get_drone_permissions_(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve all drone permissions.
    """
    return await get_drone_permissions(db=db)


@router.post(
    "",
    response_model=DronePermission,
    dependencies=[Depends(requires_superadmin_async)],
)
async def create_drone_permission_(
    drone_permission: DronePermissionCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new drone permission.
    """
    return await create_drone_permission(db=db, drone_permission=drone_permission)


@router.put(
    "/{drone_integration_id}/{company_id}",
    response_model=DronePermission,
    dependencies=[Depends(requires_superadmin_async)],
)
async def update_drone_permission_(
    drone_integration_id: int,
    company_id: uuid.UUID,
    drone_permission: DronePermissionUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update a drone permission.
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
    """
    Delete a drone permission.
    """
    await delete_drone_permission(
        db=db,
        drone_integration_id=drone_integration_id,
        company_id=company_id,
    )
    return HTTPException(status_code=200, detail="Drone permission deleted")
