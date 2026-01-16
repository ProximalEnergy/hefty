from typing import Annotated

from core.crud.operational.device_models import get_device_models
from core.db_query import OutputType
from fastapi import APIRouter, Query

from app import interfaces

DESCRIPTION_404 = "Device model not found"

router = APIRouter(prefix="/device-models", tags=["device_models"])


@router.get(
    "",
    response_model=list[interfaces.DeviceModel],
    operation_id="get_device_models",
)
async def get_device_models_route(
    device_model_ids: Annotated[list[int], Query()] = [],
    device_type_ids: Annotated[list[int], Query()] = [],
):
    """Get device models.

    Args:
        device_model_ids: Optional list of device model IDs to filter by.
        device_type_ids: Optional list of device type IDs to filter by.
    """
    df = await get_device_models(
        deep=False,
        device_model_ids=device_model_ids or None,
        device_type_ids=device_type_ids or None,
    ).get_async(output_type=OutputType.PANDAS)

    return df.to_dict(orient="records")
