from typing import Annotated

from core.crud.operational.device_types import get_device_type as crud_get_device_type
from core.crud.operational.device_types import get_device_types as crud_get_device_types
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces, utils
from app.dependencies import get_async_db

DESCRIPTION_404 = "Device type not found"

router = APIRouter(prefix="/device-types", tags=["device_types"])


@router.get(
    "", response_model=list[interfaces.DeviceType], operation_id="get_device_types"
)
async def get_device_types(
    device_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    name_long: str = "",
    only_included_by_default: bool = True,
    db: AsyncSession = Depends(get_async_db),
):
    """todo

    Args:
        device_type_ids: TODO: describe.
        name_short: TODO: describe.
        name_long: TODO: describe.
        only_included_by_default: TODO: describe.
        db: TODO: describe.
    """
    return await crud_get_device_types(
        db=db,
        device_type_ids=device_type_ids,
        name_short=name_short,
        name_long=name_long,
        only_included_by_default=only_included_by_default,
    )


@router.get(
    "/{device_type_id}",
    response_model=interfaces.DeviceType,
    responses={404: {"description": DESCRIPTION_404}},
    operation_id="get_device_type_by_id",
)
async def get_device_type(
    device_type_id: int, db: Annotated[AsyncSession, Depends(get_async_db)]
):
    """todo

    Args:
        device_type_id: TODO: describe.
        db: TODO: describe.
    """
    device_type = await crud_get_device_type(db=db, device_type_id=device_type_id)
    utils.check_404(value=device_type, detail=DESCRIPTION_404)
    return device_type
