from typing import Annotated

from core.crud.operational.sensor_types import (
    get_sensor_type as core_get_sensor_type,
)
from core.crud.operational.sensor_types import (
    get_sensor_types as core_get_sensor_types,
)
from core.database import get_db
from core.db_query import OutputType
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
from app._dependencies.authentication import get_user

DESCRIPTION_404 = "Sensor type not found"

router = APIRouter(prefix="/sensor-types", tags=["sensor_types"])


@router.get(
    "", response_model=list[interfaces.SensorType], operation_id="get_sensor_types"
)
async def get_sensor_types(
    sensor_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    name_long: str = "",
    name_metric: str = "",
    unit: str = "",
):
    """todo

    Args:
        sensor_type_ids: Description for sensor_type_ids.
        name_short: Description for name_short.
        name_long: Description for name_long.
        name_metric: Description for name_metric.
        unit: Description for unit.
    """
    df = await core_get_sensor_types(
        sensor_type_ids=sensor_type_ids,
        name_short=name_short,
        name_long=name_long,
        name_metric=name_metric,
        unit=unit,
    ).get_async(output_type=OutputType.PANDAS)

    return interfaces.normalize_pandas_nullable(content=df.to_dict(orient="records"))


@router.get(
    "/{sensor_type_id}",
    response_model=interfaces.SensorType,
    responses={404: {"description": DESCRIPTION_404}},
    operation_id="get_sensor_type",
)
async def get_sensor_type(sensor_type_id: int):
    """todo

    Args:
        sensor_type_id: Description for sensor_type_id.
    """
    sensor_type = await core_get_sensor_type(
        sensor_type_id=sensor_type_id,
    ).get_async(output_type=OutputType.SQLALCHEMY)
    utils.check_404(value=sensor_type, detail=DESCRIPTION_404)
    return sensor_type


@router.post(
    "",
    response_model=interfaces.SensorType,
    operation_id="create_sensor_type",
)
def create_sensor_type(
    sensor_type: interfaces.SensorType,
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Create a new sensor type. Only superadmins can create sensor types.

    Args:
        sensor_type: Description for sensor_type.
        user_data: Description for user_data.
        db: Description for db.
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
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Update an existing sensor type. Only superadmins can update sensor types.

    Args:
        sensor_type_id: Description for sensor_type_id.
        sensor_type: Description for sensor_type.
        user_data: Description for user_data.
        db: Description for db.
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
