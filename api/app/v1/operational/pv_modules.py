import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.operational.pv_modules import (
    create_pv_module as crud_create_pv_module,
)
from app._crud.operational.pv_modules import (
    get_pv_module_by_id as crud_get_pv_module_by_id,
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
from app.domain.equipment.pv_module._utils.single_diode_params import (
    calc_reference_params,
)
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
    """
    Get PV module IDs for each manufacturer and model pair.

    Returns corresponding PV module IDs in the same order. Returns None for any pairs
    that don't exist in the database.

    The input lists must have the same length.
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
    """
    Create a new PV module or update an existing one.

    If a PV module with the same pv_module_id already exists, it will be updated.
    If the PV module doesn't exist, a new one will be created.
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
    """
    Upload an PAN file and retrieve pv module information from it.

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


@router.put(
    "/recalculate-single-diode",
    response_model=interfaces.PVModule,
    summary="Recalculate single diode parameters for a PV module",
)
async def recalculate_single_diode_parameters(
    *,
    pv_module_id: int,
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """
    Get a PV module from the database, recalculate its single diode parameters,
    and update the database with the new parameters.

    """
    try:
        # Get the existing PV module from the database
        existing_module = await crud_get_pv_module_by_id(
            db=db,
            pv_module_id=pv_module_id,
            company_id=authorized_company_id,
        )

        if not existing_module:
            raise HTTPException(
                status_code=404,
                detail=f"PV module with ID {pv_module_id} not found",
            )

        # Convert the database model to a dictionary for calc_reference_params
        module_dict = {
            "vmp": existing_module.vmp,
            "imp": existing_module.imp,
            "voc": existing_module.voc,
            "isc": existing_module.isc,
            "alpha_isc": existing_module.alpha_isc,
            "beta_voc": existing_module.beta_voc,
            "cells_in_series": existing_module.cells_in_series,
            "eg": existing_module.eg,
            "degdt": existing_module.degdt,
            "technology": existing_module.technology,
        }

        # Recalculate single diode parameters
        updated_module_dict = calc_reference_params(pv_module=module_dict)

        # Create updated PVModule interface object
        updated_pv_module = interfaces.PVModule(
            pv_module_id=existing_module.pv_module_id,
            company_id=existing_module.company_id,
            manufacturer=existing_module.manufacturer,
            model=existing_module.model,
            technology=existing_module.technology,
            bifaciality_factor=existing_module.bifaciality_factor,
            pmax=existing_module.pmax,
            isc=existing_module.isc,
            voc=existing_module.voc,
            imp=existing_module.imp,
            vmp=existing_module.vmp,
            gamma_pmax=existing_module.gamma_pmax,
            alpha_isc_relative=None,
            beta_voc_relative=None,
            alpha_isc=existing_module.alpha_isc,
            beta_voc=existing_module.beta_voc,
            warranted_degradation_rate=existing_module.warranted_degradation_rate,
            warranted_degradation_initial=existing_module.warranted_degradation_initial,
            length=existing_module.length,
            width=existing_module.width,
            frame_overhang=existing_module.frame_overhang,
            has_ar_coating=existing_module.has_ar_coating,
            cells_in_series=existing_module.cells_in_series,
            cells_in_parallel=existing_module.cells_in_parallel,
            # Updated single diode parameters from calc_reference_params
            photocurrent=updated_module_dict["photocurrent"],
            diode_saturation_current=updated_module_dict["diode_saturation_current"],
            r_series=updated_module_dict["r_series"],
            r_shunt=updated_module_dict["r_shunt"],
            modified_ideality_factor=updated_module_dict["modified_ideality_factor"],
            eg=existing_module.eg or 1.1,
            degdt=existing_module.degdt or 0.0002,
            data_source=existing_module.data_source or "recalculated",
            family=existing_module.family or "unknown",
            half_cut=existing_module.half_cut,
        )

        # Update the database with recalculated parameters
        db_pv_module = await crud_create_pv_module(
            db=db,
            pv_module=updated_pv_module,
        )

        return db_pv_module

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not recalculate single diode parameters: {str(e)}",
        )
