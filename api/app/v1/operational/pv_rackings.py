import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.operational.rackings import (
    create_racking as crud_create_racking,
)
from app._crud.operational.rackings import (
    get_racking_ids_by_manufacturer_model,
    get_racking_manufacturers,
    get_racking_models_given_manufacturer,
)
from app._crud.operational.rackings import (
    get_rackings as crud_get_racking,
)
from app._dependencies.authorization import require_user_company

# --- Routes ---
router = APIRouter(prefix="/pv-rackings", tags=["pv_rackings"])


@router.get(
    "",
    response_model=list[interfaces.PVRackings],
    operation_id="get_rackings",
)
async def get_racking(
    *,
    racking_ids: Annotated[list[int], Query()] = [],
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    # authorized_company_id = None
    """todo

    Args:
        racking_ids: Description for racking_ids.
        db: Description for db.
    """
    return await crud_get_racking(
        db=db,
        racking_ids=racking_ids,
    )


@router.get(
    "/manufacturers",
    summary="Get all PV racking manufacturers from the proximal database",
    operation_id="get_proximal_racking_manufacturers",
)
async def get_proximal_racking_manufacturers(
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """todo

    Args:
        authorized_company_id: Description for authorized_company_id.
        db: Description for db.
    """
    manufacturers = await get_racking_manufacturers(
        db=db, company_id=authorized_company_id
    )
    return manufacturers


@router.get(
    "/models",
    summary=(
        "Get all PV racking models from the proximal database, "
        "optionally filtered by a selected manufacturer"
    ),
    operation_id="get_proximal_racking_models_given_manufacturer",
)
async def get_proximal_racking_models(
    manufacturer: str | None = None,
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """todo

    Args:
        manufacturer: Description for manufacturer.
        authorized_company_id: Description for authorized_company_id.
        db: Description for db.
    """
    models = await get_racking_models_given_manufacturer(
        db=db, manufacturer=manufacturer, company_id=authorized_company_id
    )
    return models


@router.get(
    "/lookup-ids",
    summary="Get racking IDs based on manufacturer and model pairs",
    response_model=list[int | None],
    operation_id="get_racking_ids_by_manufacturer_and_model",
)
async def get_racking_ids_by_manufacturer_and_model(
    *,
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    manufacturers: Annotated[list[str], Query()],
    models: Annotated[list[str], Query()],
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """Get racking IDs for each manufacturer and model pair.

        corresponding racking IDs in the same order. Returns None for any pairs
        that don't exist in the database.

        The input lists must have the same length.

    Args:
        authorized_company_id: Description for authorized_company_id.
        manufacturers: Description for manufacturers.
        models: Description for models.
        db: Description for db.
    """
    try:
        racking_ids = await get_racking_ids_by_manufacturer_model(
            db=db,
            racking_manufacturers=manufacturers,
            racking_models=models,
            company_id=authorized_company_id,
        )
        return racking_ids
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post(
    "",
    response_model=interfaces.PVRackings,
    summary="Create or update a PV racking",
    operation_id="create_racking",
)
async def create_racking_route(
    *,
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    racking: interfaces.PVRackings,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """Create a new PV racking or update an existing one.

        If a racking with the same model already exists, it will be updated.
        If the racking doesn't exist, a new one will be created.

    Args:
        authorized_company_id: Description for authorized_company_id.
        racking: Description for racking.
        db: Description for db.
    """
    if authorized_company_id is None:
        raise HTTPException(
            status_code=403,
            detail="A company ID is required to create a new racking",
        )

    try:
        racking.company_id = authorized_company_id
        db_racking = await crud_create_racking(
            db=db,
            racking=racking,
        )
        return db_racking
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not create or update racking: {str(e)}",
        )
