from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces, utils
from app._crud.operational.data_types import get_data_type as crud_get_data_type
from app._crud.operational.data_types import get_data_types as crud_get_data_types
from app.dependencies import get_async_db

DESCRIPTION_404 = "Data type not found"

router = APIRouter(prefix="/data-types", tags=["data_types"])


@router.get("", response_model=list[interfaces.DataType])
async def get_data_types(
    data_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    db: AsyncSession = Depends(get_async_db),
):
    """todo

    Args:
        data_type_ids: TODO: describe.
        name_short: TODO: describe.
        db: TODO: describe.
    """
    return await crud_get_data_types(
        db, data_type_ids=data_type_ids, name_short=name_short
    )


@router.get(
    "/{data_type_id}",
    response_model=interfaces.DataType,
    responses={404: {"description": DESCRIPTION_404}},
)
async def get_data_type(
    data_type_id: int, db: Annotated[AsyncSession, Depends(get_async_db)]
):
    """todo

    Args:
        data_type_id: TODO: describe.
        db: TODO: describe.
    """
    data_type = await crud_get_data_type(db, data_type_id=data_type_id)
    utils.check_404(value=data_type, detail=DESCRIPTION_404)
    return data_type
