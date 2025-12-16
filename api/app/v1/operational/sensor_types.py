from typing import Annotated

from core.crud.operational.sensor_types import (
    get_sensor_type as core_get_sensor_type,
)
from core.crud.operational.sensor_types import (
    get_sensor_types as core_get_sensor_types,
)
from core.dependencies import get_db
from core.enumerations import SensorType, UserTypeEnum
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import interfaces, utils
from app._crud.operational.sensor_types import (
    create_sensor_type as crud_create_sensor_type,
)
from app._crud.operational.sensor_types import (
    get_next_sensor_type_id as crud_get_next_sensor_type_id,
)
from app._crud.operational.sensor_types import (
    update_sensor_type as crud_update_sensor_type,
)
from app.dependencies import get_user_data_async

DESCRIPTION_404 = "Sensor type not found"

router = APIRouter(prefix="/sensor-types", tags=["sensor_types"])


@router.get(
    "", response_model=list[interfaces.SensorType], operation_id="get_sensor_types"
)
def get_sensor_types(
    sensor_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    name_long: str = "",
    name_metric: str = "",
    unit: str = "",
    db: Session = Depends(get_db),
):
    """todo

    Args:
        sensor_type_ids: TODO: describe.
        name_short: TODO: describe.
        name_long: TODO: describe.
        name_metric: TODO: describe.
        unit: TODO: describe.
        db: TODO: describe.
    """
    return core_get_sensor_types(
        db,
        sensor_type_ids=sensor_type_ids,
        name_short=name_short,
        name_long=name_long,
        name_metric=name_metric,
        unit=unit,
    ).models()


@router.get(
    "/{sensor_type_id}",
    response_model=interfaces.SensorType,
    responses={404: {"description": DESCRIPTION_404}},
    operation_id="get_sensor_type",
)
def get_sensor_type(sensor_type_id: int, db: Annotated[Session, Depends(get_db)]):
    """todo

    Args:
        sensor_type_id: TODO: describe.
        db: TODO: describe.
    """
    sensor_type = core_get_sensor_type(
        db=db,
        sensor_type_id=sensor_type_id,
    ).item
    utils.check_404(value=sensor_type, detail=DESCRIPTION_404)
    return sensor_type


@router.post(
    "",
    response_model=interfaces.SensorType,
    operation_id="create_sensor_type",
)
def create_sensor_type(
    sensor_type: interfaces.SensorType,
    user_data: Annotated[interfaces.UserData, Depends(get_user_data_async)],
    db: Annotated[Session, Depends(get_db)],
):
    """Create a new sensor type. Only superadmins can create sensor types.

    Args:
        sensor_type: TODO: describe.
        user_data: TODO: describe.
        db: TODO: describe.
    """
    if user_data.user_type_id != UserTypeEnum.SUPERADMIN:
        raise HTTPException(
            status_code=403, detail="Only superadmins can create sensor types"
        )

    # Get next available ID if not provided
    if sensor_type.sensor_type_id == SensorType.GHOST_UNKNOWN:
        sensor_type.sensor_type_id = crud_get_next_sensor_type_id(db=db)

    try:
        return crud_create_sensor_type(db=db, sensor_type=sensor_type)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Could not create sensor type: {str(e)}"
        )


@router.put(
    "/{sensor_type_id}",
    response_model=interfaces.SensorType,
    responses={404: {"description": DESCRIPTION_404}},
    operation_id="update_sensor_type",
)
def update_sensor_type(
    sensor_type_id: int,
    sensor_type: interfaces.SensorType,
    user_data: Annotated[interfaces.UserData, Depends(get_user_data_async)],
    db: Annotated[Session, Depends(get_db)],
):
    """Update an existing sensor type. Only superadmins can update sensor types.

    Args:
        sensor_type_id: TODO: describe.
        sensor_type: TODO: describe.
        user_data: TODO: describe.
        db: TODO: describe.
    """
    if user_data.user_type_id != UserTypeEnum.SUPERADMIN:
        raise HTTPException(
            status_code=403, detail="Only superadmins can update sensor types"
        )

    # Ensure the ID in the path matches the ID in the body
    sensor_type.sensor_type_id = sensor_type_id

    try:
        updated_sensor_type = crud_update_sensor_type(
            db=db, sensor_type_id=sensor_type_id, sensor_type=sensor_type
        )
        if not updated_sensor_type:
            raise HTTPException(status_code=404, detail=DESCRIPTION_404)
        return updated_sensor_type
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Could not update sensor type: {str(e)}"
        )
