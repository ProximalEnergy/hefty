from typing import Annotated

from core.crud.operational.device_models import (
    get_device_models as crud_get_device_models,
)
from core.dependencies import get_db
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import interfaces

DESCRIPTION_404 = "Device model not found"

router = APIRouter(prefix="/device-models", tags=["device_models"])


@router.get(
    "",
    response_model=list[interfaces.DeviceModel],
    operation_id="get_device_models",
)
def get_device_models(
    device_model_ids: Annotated[list[int], Query()] = [],
    device_type_ids: Annotated[list[int], Query()] = [],
    db: Session = Depends(get_db),
):
    """Get device models.

    Args:
        device_model_ids: Optional list of device model IDs to filter by.
        device_type_ids: Optional list of device type IDs to filter by.
        db: Database session.
    """
    return crud_get_device_models(
        db=db,
        deep=False,
        device_model_ids=device_model_ids if device_model_ids else None,
        device_type_ids=device_type_ids if device_type_ids else None,
    ).models()
