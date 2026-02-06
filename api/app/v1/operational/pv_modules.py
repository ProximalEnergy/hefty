import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.operational.pv_modules import (
    create_pv_module as crud_create_pv_module,
)
from app._crud.operational.pv_modules import (
    get_pv_module_ids as crud_get_pv_module_ids,
)
from app._crud.operational.pv_modules import (
    get_pv_module_ids_by_manufacturer_model,
    get_pv_module_manufacturers,
    get_pv_module_models_given_manufacturer,
)
from app._crud.operational.pv_modules import (
    get_pv_modules as crud_get_pv_modules,
)
from app._dependencies.authorization import require_user_company
from app.domain.equipment.pv_module.parse_pan.c_parse_pan import parse_pan

# --- Routes ---
router = APIRouter(prefix="/pv-modules", tags=["pv_modules"])


@router.get(
    "",
    response_model=list[interfaces.PVModule],
    operation_id="get_pv_modules",
    dependencies=[Depends(require_user_company)],
)
async def get_pv_modules(
    *,
    pv_module_ids: Annotated[list[int], Query()] = [],
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """todo

    Args:
        pv_module_ids: Description for pv_module_ids.
        db: Description for db.
    """
    return await crud_get_pv_modules(
        db=db,
        pv_module_ids=pv_module_ids,
    )


@router.get("/ids", response_model=list[int], operation_id="get_pv_module_ids")
async def get_pv_module_ids(
    *,
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    pv_module_manufacturer: Annotated[list[str], Query()] = [],
    pv_module_model: Annotated[list[str], Query()] = [],
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """todo

    Args:
        authorized_company_id: Description for authorized_company_id.
        pv_module_manufacturer: Description for pv_module_manufacturer.
        pv_module_model: Description for pv_module_model.
        db: Description for db.
    """
    return await crud_get_pv_module_ids(
        db=db,
        pv_module_manufacturers=pv_module_manufacturer,
        pv_module_models=pv_module_model,
        company_id=authorized_company_id,
    )


@router.get(
    "/manufacturers",
    summary="Get all PV module manufacturers from the proximal database",
    operation_id="get_proximal_pv_module_manufacturers",
)
async def get_proximal_pv_module_manufacturers(
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """todo

    Args:
        authorized_company_id: Description for authorized_company_id.
        db: Description for db.
    """
    manufacturers = await get_pv_module_manufacturers(
        db=db, company_id=authorized_company_id
    )
    return manufacturers


@router.get(
    "/models",
    summary=(
        "Get all PV module models from the proximal database, "
        "optionally filtered by a selected manufacturer"
    ),
    operation_id="get_proximal_pv_module_models_given_manufacturer",
)
async def get_proximal_pv_module_models(
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
    models = await get_pv_module_models_given_manufacturer(
        db=db, manufacturer=manufacturer, company_id=authorized_company_id
    )
    return models


@router.get(
    "/lookup-ids",
    summary="Get PV module IDs based on manufacturer and model pairs",
    response_model=list[int | None],
)
async def get_pv_module_ids_by_manufacturer_and_model(
    *,
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    manufacturers: Annotated[list[str], Query()],
    models: Annotated[list[str], Query()],
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """Get PV module IDs for each manufacturer and model pair.

    Returns corresponding PV module IDs in the same order. Returns None for
    any pairs that don't exist in the database.

    The input lists must have the same length.

    Args:
        authorized_company_id: Description for authorized_company_id.
        manufacturers: Description for manufacturers.
        models: Description for models.
        db: Description for db.
    """
    try:
        pv_module_ids = await get_pv_module_ids_by_manufacturer_model(
            db=db,
            pv_module_manufacturers=manufacturers,
            pv_module_models=models,
            company_id=authorized_company_id,
        )
        return pv_module_ids
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post(
    "",
    response_model=interfaces.PVModule,
    summary="Create or update a PV module",
)
async def create_pv_module(
    *,
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    pv_module: interfaces.PVModule,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """Create a new PV module or update an existing one.

        If a PV module with the same pv_module_id already exists, it will be updated.
        If the PV module doesn't exist, a new one will be created.

    Args:
        authorized_company_id: Description for authorized_company_id.
        pv_module: Description for pv_module.
        db: Description for db.
    """
    if authorized_company_id is None:
        pass
    else:
        pv_module.company_id = authorized_company_id

    try:
        db_pv_module = await crud_create_pv_module(
            db=db,
            pv_module=pv_module,
        )
        return db_pv_module
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not create or update PV module: {str(e)}",
        )


@router.post(
    "/parse-pan",
    summary="Parse PAN file and return pv_module information",
    response_model=dict[str, Any],
)
async def parse_pan_file(
    *,
    file: UploadFile = File(...),
):
    """Upload an PAN file and retrieve pv module information from it.

        This endpoint accepts an PAN file upload, processes it using the parse_pan
        function,
        and returns the extracted information in JSON format.

        The processing pipeline includes:
        1. Reading the PAN file structure
        2. Formatting the data into a standardized pv_module configuration

        Returns:
            A JSON object with the following structure:
            - success: Boolean indicating if parsing was successful
            - message: Status message
            - pv_module_data: The complete pv_module configuration with all parameters

    Args:
        file: Uploaded PAN file to parse.
    """
    try:
        file_content = await file.read()
        result = parse_pan(
            file_content=file_content,
        )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error parsing PAN file: {str(e)}",
        )
