from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces, utils
from app._crud.operational.device_types import get_device_type as crud_get_device_type
from app._crud.operational.device_types import get_device_types as crud_get_device_types
from app.dependencies import get_async_db

DESCRIPTION_404 = "Device type not found"

router = APIRouter(prefix="/device-types", tags=["device_types"])
deprecated_router = APIRouter(
    prefix="/device_types", tags=["device_types"], deprecated=True
)


@router.get(
    "/", response_model=list[interfaces.DeviceType], operation_id="get_device_types"
)
async def get_device_types(
    device_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    name_long: str = "",
    only_included_by_default: bool = True,
    db: AsyncSession = Depends(get_async_db),
):
    return await crud_get_device_types(
        db=db,
        device_type_ids=device_type_ids,
        name_short=name_short,
        name_long=name_long,
        only_included_by_default=only_included_by_default,
    )


@deprecated_router.get(
    "/",
    response_model=list[interfaces.DeviceType],
    operation_id="get_device_types_legacy",
)
async def get_device_types_legacy(
    device_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    name_long: str = "",
    only_included_by_default: bool = True,
    db: AsyncSession = Depends(get_async_db),
):
    return await get_device_types(
        device_type_ids=device_type_ids,
        name_short=name_short,
        name_long=name_long,
        only_included_by_default=only_included_by_default,
        db=db,
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
    device_type = await crud_get_device_type(db=db, device_type_id=device_type_id)
    utils.check_404(value=device_type, detail=DESCRIPTION_404)
    return device_type


@deprecated_router.get(
    "/{device_type_id}",
    response_model=interfaces.DeviceType,
    responses={404: {"description": DESCRIPTION_404}},
    operation_id="get_device_type_by_id_legacy",
)
async def get_device_type_legacy(
    device_type_id: int, db: Annotated[AsyncSession, Depends(get_async_db)]
):
    return await get_device_type(device_type_id, db)
