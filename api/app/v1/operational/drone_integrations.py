import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.operational.drone_integrations import (
    create_drone_integration,
    delete_drone_integration,
    get_drone_integrations,
    update_drone_integration,
)
from app.dependencies import get_async_db, requires_superadmin_async
from app.interfaces import (
    DroneIntegration,
    DroneIntegrationCreate,
    DroneIntegrationUpdate,
)

router = APIRouter(prefix="/drone-integrations")
logger = logging.getLogger(__name__)


@router.get("", response_model=list[DroneIntegration])
async def get_drone_integrations_(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve all drone integrations.
    """
    return await get_drone_integrations(db=db)


@router.post(
    "",
    response_model=DroneIntegration,
    dependencies=[Depends(requires_superadmin_async)],
)
async def create_drone_integration_(
    drone_integration: DroneIntegrationCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new drone integration.
    """
    return await create_drone_integration(db=db, drone_integration=drone_integration)


@router.put(
    "/{drone_integration_id}",
    response_model=DroneIntegration,
    dependencies=[Depends(requires_superadmin_async)],
)
async def update_drone_integration_(
    drone_integration_id: int,
    drone_integration: DroneIntegrationUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update a drone integration.
    """
    return await update_drone_integration(
        db=db,
        drone_integration_id=drone_integration_id,
        drone_integration=drone_integration,
    )


@router.delete(
    "/{drone_integration_id}", dependencies=[Depends(requires_superadmin_async)]
)
async def delete_drone_integration_(
    drone_integration_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete a drone integration.
    """
    await delete_drone_integration(db=db, drone_integration_id=drone_integration_id)
    return HTTPException(status_code=200, detail="Drone integration deleted")
