from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.operational.failure_modes import (
    get_failure_modes as crud_get_failure_modes,
)
from app.dependencies import get_async_db

router = APIRouter(prefix="/failure-modes", tags=["failure-modes"])


@router.get("/", operation_id="get_failure_modes")
async def get_failure_modes(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    failure_mode_ids: Annotated[list[int], Query()] = [],
):
    failure_modes = await crud_get_failure_modes(
        db=db, failure_mode_ids=failure_mode_ids
    )
    return failure_modes
