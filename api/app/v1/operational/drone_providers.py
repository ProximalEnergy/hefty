from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.operational.drone_providers import (
    create_drone_provider,
    delete_drone_provider,
    get_drone_providers,
    update_drone_provider,
)
from app.dependencies import get_async_db, requires_superadmin_async
from app.interfaces import (
    DroneProviderCreate,
    DroneProviderInterface,
    DroneProviderUpdate,
)

router = APIRouter(prefix="/drone-providers")


@router.get("", response_model=list[DroneProviderInterface])
async def get_drone_providers_(
    db: AsyncSession = Depends(get_async_db),
):
    """Retrieve all drone providers.

    Args:
        db: Async database session.
    """
    return await get_drone_providers(db=db)


@router.post(
    "",
    response_model=DroneProviderInterface,
    dependencies=[Depends(requires_superadmin_async)],
)
async def create_drone_provider_(
    drone_provider: DroneProviderCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new drone provider.

    Args:
        drone_provider: Payload describing the new provider.
        db: Async database session.
    """
    return await create_drone_provider(db=db, drone_provider=drone_provider)


@router.put(
    "/{drone_provider_id}",
    response_model=DroneProviderInterface,
    dependencies=[Depends(requires_superadmin_async)],
)
async def update_drone_provider_(
    drone_provider_id: int,
    drone_provider: DroneProviderUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """Update a drone provider.

    Args:
        drone_provider_id: Provider identifier to update.
        drone_provider: Payload of updated provider fields.
        db: Async database session.
    """
    return await update_drone_provider(
        db=db,
        drone_provider_id=drone_provider_id,
        drone_provider=drone_provider,
    )


@router.delete(
    "/{drone_provider_id}", dependencies=[Depends(requires_superadmin_async)]
)
async def delete_drone_provider_(
    drone_provider_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a drone provider.

    Args:
        drone_provider_id: Provider identifier to delete.
        db: Async database session.
    """
    await delete_drone_provider(db=db, drone_provider_id=drone_provider_id)
    return HTTPException(status_code=200, detail="Drone provider deleted")
