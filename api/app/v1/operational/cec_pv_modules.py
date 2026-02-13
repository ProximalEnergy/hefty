from typing import Annotated

from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from app._crud.operational.cec_pv_modules import (
    get_cec_pv_module_ids_by_manufacturer_model,
    get_cec_pv_module_manufacturers,
    get_cec_pv_module_models_given_manufacturer,
)
from app._crud.operational.cec_pv_modules import (
    get_cec_pv_modules as crud_get_cec_pv_modules,
)
from app._crud.operational.cec_pv_modules import (
    upsert_cec_pv_modules_bulk as crud_upsert_cec_pv_modules_bulk,
)
from app.dependencies import get_async_db
from app.domain.equipment.pv_module.parse_cec.c_calc_parameters import (
    adapt_cec_pv_module_to_proximal,
)

DESCRIPTION_404 = "CEC PV Module not found"

router = APIRouter(prefix="/cec-pv-modules", tags=["cec_pv_modules"])


@router.get("", response_model=list[interfaces.CECPVModuleWithID])
async def get_cec_pv_modules(
    cec_pv_module_ids: Annotated[list[int], Query()] = [],
):
    """todo

    Args:
        cec_pv_module_ids: Description for cec_pv_module_ids.
    """
    cec_pv_modules = await crud_get_cec_pv_modules(
        cec_pv_module_ids=cec_pv_module_ids,
    ).get_async(output_type=OutputType.PANDAS)
    return cec_pv_modules.to_dict("records")


@router.get("/proximal-format", response_model=dict)
async def get_cec_pv_modules_in_proximal_format(
    cec_pv_module_id: int,
):
    """todo

    Args:
        cec_pv_module_id: Description for cec_pv_module_id.
    """
    cec_pv_modules = await crud_get_cec_pv_modules(
        cec_pv_module_ids=[cec_pv_module_id],
    ).get_async(output_type=OutputType.SQLALCHEMY)
    if not cec_pv_modules:
        raise HTTPException(status_code=404, detail=DESCRIPTION_404)
    cec_pv_module = cec_pv_modules[0]
    cec_pv_module_validated = interfaces.CECPVModule.model_validate(cec_pv_module)
    cec_pv_module_adapted = adapt_cec_pv_module_to_proximal(
        cec_pv_module=cec_pv_module_validated,
    )
    return cec_pv_module_adapted


@router.get(
    "/lookup-ids",
    summary="Get CEC PV module IDs based on manufacturer and model pairs",
    response_model=list[int | None],
)
async def get_cec_pv_module_ids_by_manufacturer_and_model(
    *,
    manufacturers: Annotated[list[str], Query()],
    models: Annotated[list[str], Query()],
    db: AsyncSession = Depends(get_async_db),
):
    """Get CEC PV module IDs for each manufacturer and model pair.

    Returns corresponding CEC PV module IDs in the same order. Returns None
    for any pairs that don't exist in the database.

    The input lists must have the same length.

    Args:
        manufacturers: Description for manufacturers.
        models: Description for models.
        db: Description for db.
    """
    try:
        cec_pv_module_ids = await get_cec_pv_module_ids_by_manufacturer_model(
            db=db,
            pv_module_manufacturers=manufacturers,
            pv_module_models=models,
        )
        return cec_pv_module_ids
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.get(
    "/manufacturers",
    summary="Get all CEC PV module manufacturers from the database",
)
async def get_proximal_cec_pv_module_manufacturers(
    db: AsyncSession = Depends(get_async_db),
):
    """todo

    Args:
        db: Description for db.
    """
    manufacturers = await get_cec_pv_module_manufacturers(db=db)
    return manufacturers


@router.get(
    "/models",
    summary=(
        "Get all CEC PV module models from the database, "
        "optionally filtered by a selected manufacturer"
    ),
)
async def get_proximal_cec_pv_module_models(
    db: AsyncSession = Depends(get_async_db),
    manufacturer: str | None = None,
):
    """todo

    Args:
        db: Description for db.
        manufacturer: Description for manufacturer.
    """
    models = await get_cec_pv_module_models_given_manufacturer(
        db=db,
        manufacturer=manufacturer,
    )
    return models


@router.post("", response_model=list[interfaces.CECPVModule])
async def upsert_cec_pv_modules_bulk(
    modules: interfaces.CECPVModuleBulkCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    """todo

    Args:
        modules: Description for modules.
        db: Description for db.
    """
    return await crud_upsert_cec_pv_modules_bulk(db, modules=modules.modules)
