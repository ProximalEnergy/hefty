import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.operational.inverters import (
    create_inverter as crud_create_inverter,
)
from app._crud.operational.inverters import (
    get_inverter_by_id as crud_get_inverter_by_id,
)
from app._crud.operational.inverters import (
    get_inverter_ids as crud_get_inverter_ids,
)
from app._crud.operational.inverters import (
    get_inverter_ids_by_manufacturer_model,
    get_inverter_manufacturers,
    get_inverter_models_given_manufacturer,
)
from app._crud.operational.inverters import (
    get_inverters as crud_get_inverters,
)
from app._dependencies.authorization import require_user_company
from app.domain.equipment.inverter.parse_ond.c_parse_ond import parse_ond
from app.domain.equipment.inverter.parse_ond.s04_calc_sandia_fit import calc_fit_sandia

# --- Routes ---
router = APIRouter(prefix="/pv-inverters", tags=["pv_inverters"])


@router.get(
    "",
    response_model=list[interfaces.Inverter],
    operation_id="get_inverters",
)
async def get_inverters_route(
    *,
    inverter_ids: Annotated[list[int], Query()] = [],
    device_model_ids: Annotated[list[int], Query()] = [],
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """todo

    Args:
        inverter_ids: Description for inverter_ids.
        device_model_ids: Description for device_model_ids.
        db: Description for db.
    """
    return await crud_get_inverters(
        db=db,
        inverter_ids=inverter_ids,
        device_model_ids=device_model_ids,
    )


@router.get(
    "/ids",
    response_model=list[int],
    operation_id="get_inverter_ids",
)
async def get_inverter_ids_route(
    *,
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    inverter_manufacturer: Annotated[list[str], Query()] = [],
    inverter_model: Annotated[list[str], Query()] = [],
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """todo

    Args:
        authorized_company_id: Description for authorized_company_id.
        inverter_manufacturer: Description for inverter_manufacturer.
        inverter_model: Description for inverter_model.
        db: Description for db.
    """
    return await crud_get_inverter_ids(
        db=db,
        inverter_manufacturer=inverter_manufacturer,
        inverter_model=inverter_model,
        company_id=authorized_company_id,
    )


@router.get(
    "/manufacturers",
    summary="Get all PV inverter manufacturers from the proximal database",
    operation_id="get_proximal_inverter_manufacturers",
)
async def get_proximal_inverter_manufacturers(
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """todo

    Args:
        authorized_company_id: Description for authorized_company_id.
        db: Description for db.
    """
    manufacturers = await get_inverter_manufacturers(
        db=db,
        company_id=authorized_company_id,
    )
    return manufacturers


@router.get(
    "/models",
    summary=(
        "Get all PV inverter models from the proximal database, "
        "optionally filtered by a selected manufacturer"
    ),
    operation_id="get_proximal_inverter_models_given_manufacturer",
)
async def get_proximal_inverter_models(
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
    models = await get_inverter_models_given_manufacturer(
        db=db, manufacturer=manufacturer, company_id=authorized_company_id
    )
    return models


@router.get(
    "/lookup-ids",
    summary="Get inverter IDs based on manufacturer and model pairs",
    response_model=list[int | None],
    operation_id="get_inverter_ids_by_manufacturer_and_model",
)
async def get_inverter_ids_by_manufacturer_and_model(
    *,
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    manufacturers: Annotated[list[str], Query()],
    models: Annotated[list[str], Query()],
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """Get inverter IDs for each manufacturer and model pair.

        corresponding inverter IDs in the same order. Returns None for any pairs
        that don't exist in the database.

        The input lists must have the same length.

    Args:
        authorized_company_id: Description for authorized_company_id.
        manufacturers: Description for manufacturers.
        models: Description for models.
        db: Description for db.
    """
    try:
        inverter_ids = await get_inverter_ids_by_manufacturer_model(
            db=db,
            inverter_manufacturers=manufacturers,
            inverter_models=models,
            company_id=authorized_company_id,
        )
        return inverter_ids
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post(
    "",
    response_model=interfaces.Inverter,
    summary="Create or update a PV inverter",
    operation_id="create_inverter",
)
async def create_inverter_route(
    *,
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    inverter: interfaces.Inverter,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """Create a new PV inverter or update an existing one.

        If an inverter with the same inverter_id already exists, it will be updated.
        If the inverter doesn't exist, a new one will be created.

    Args:
        authorized_company_id: Description for authorized_company_id.
        inverter: Description for inverter.
        db: Description for db.
    """
    if authorized_company_id is None:
        pass
    else:
        inverter.company_id = authorized_company_id

    try:
        db_inverter = await crud_create_inverter(
            db=db,
            inverter=inverter,
        )
        return db_inverter
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not create or update inverter: {str(e)}",
        )


@router.post(
    "/parse-ond",
    summary="Parse OND file and return inverter information",
    response_model=dict[str, Any],
)
async def parse_ond_file(
    *,
    file: UploadFile = File(...),
):
    """Upload an OND file and retrieve inverter information from it.

        This endpoint accepts an OND file upload, processes it using the parse_ond
        function,
        and returns the extracted information in JSON format.

        The processing pipeline includes:
        1. Reading the OND file structure
        2. Formatting the data into a standardized inverter configuration
        3. Calculating DC nominal power
        4. Computing Sandia inverter model parameters
        5. Validating the resulting configuration

        Returns:
            A JSON object with the following structure:
            - success: Boolean indicating if parsing was successful
            - message: Status message
            - inverter_data: The complete inverter configuration with all parameters

    Args:
        file: Description for file.
    """
    try:
        file_content = await file.read()

        # Send the file content to the parse_ond function
        result = parse_ond(
            file_content=file_content,
        )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error parsing OND file: {str(e)}",
        )


@router.put(
    "/calculate-sandia",
    response_model=interfaces.Inverter,
    summary="Calculate and update Sandia parameters for an inverter",
    dependencies=[Depends(require_user_company)],
)
async def calculate_and_update_sandia_parameters(
    *,
    inverter_id: int,
    authorized_company_id: uuid.UUID | None = Depends(require_user_company),
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    # Get the inverter from the database
    """todo

    Args:
        inverter_id: Description for inverter_id.
        authorized_company_id: Description for authorized_company_id.
        db: Description for db.
    """
    db_inverter = await crud_get_inverter_by_id(
        db=db,
        inverter_id=inverter_id,
        company_id=authorized_company_id,
    )

    if not db_inverter:
        raise HTTPException(
            status_code=404,
            detail=f"Inverter with ID {inverter_id} not found",
        )

    # Convert database model to dictionary for Sandia calculation
    inverter_dict = {
        "efficiency_at_low_voltage": db_inverter.efficiency_at_low_voltage,
        "efficiency_at_mid_voltage": db_inverter.efficiency_at_mid_voltage,
        "efficiency_at_high_voltage": db_inverter.efficiency_at_high_voltage,
        "voltage_nominal_efficiency": db_inverter.voltage_nominal_efficiency,
        "power_ac_nominal": db_inverter.power_ac_nominal,
        "night_tare": db_inverter.night_tare,
    }

    try:
        # Calculate Sandia parameters
        updated_inverter_dict = calc_fit_sandia(inverter=inverter_dict)

        # Create interfaces.Inverter object with updated parameters
        updated_inverter = interfaces.Inverter(
            inverter_id=db_inverter.inverter_id,
            manufacturer=db_inverter.manufacturer,
            model=db_inverter.model,
            company_id=db_inverter.company_id,
            voltage_mpp_min=db_inverter.voltage_mpp_min,
            voltage_mpp_max=db_inverter.voltage_mpp_max,
            voltage_start_up=db_inverter.voltage_start_up,
            voltage_min=db_inverter.voltage_min,
            voltage_max=db_inverter.voltage_max,
            current_max=db_inverter.current_max,
            power_max_at_reference_temp=db_inverter.power_max_at_reference_temp,
            reference_temp=db_inverter.reference_temp,
            voltage_nominal_efficiency=db_inverter.voltage_nominal_efficiency,
            efficiency_at_low_voltage=db_inverter.efficiency_at_low_voltage,
            efficiency_at_mid_voltage=db_inverter.efficiency_at_mid_voltage,
            efficiency_at_high_voltage=db_inverter.efficiency_at_high_voltage,
            power_start_up=updated_inverter_dict["power_start_up"],
            power_ac_nominal=db_inverter.power_ac_nominal,
            power_dc_nominal=updated_inverter_dict["power_dc_nominal"],
            voltage_dc_nominal=updated_inverter_dict["voltage_dc_nominal"],
            c0=updated_inverter_dict["c0"],
            c1=updated_inverter_dict["c1"],
            c2=updated_inverter_dict["c2"],
            c3=updated_inverter_dict["c3"],
            night_tare=db_inverter.night_tare,
        )

        # Update the inverter in the database
        updated_db_inverter = await crud_create_inverter(
            db=db,
            inverter=updated_inverter,
        )

        return updated_db_inverter

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error calculating Sandia parameters: {str(e)}",
        )
