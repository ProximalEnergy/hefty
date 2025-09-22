import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio.session import AsyncSession

from app import dependencies
from app._crud.operational.calendar import (
    get_calendar_item_exceptions as crud_get_calendar_item_exceptions,
)
from app._crud.operational.calendar import (
    get_calendar_items as crud_get_calendar_items,
)

router = APIRouter(prefix="/calendar")


@router.get("/items", operation_id="get_calendar_items")
async def get_calendar_items(
    db: AsyncSession = Depends(dependencies.get_async_db),
    notifications_only: bool = False,
):
    return await crud_get_calendar_items(db=db, notifications_only=notifications_only)


@router.get("/item-exceptions")
async def get_calendar_item_exceptions(
    db: AsyncSession = Depends(dependencies.get_async_db),
    calendar_item_ids: Annotated[list[uuid.UUID], Query()] = [],
):
    return await crud_get_calendar_item_exceptions(
        db=db, calendar_item_ids=calendar_item_ids
    )
