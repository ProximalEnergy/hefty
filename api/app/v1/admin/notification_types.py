from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces, utils
from app._crud.admin.notification_types import (
    get_notification_types as crud_get_notification_types,
)

router = APIRouter(
    prefix="/notification-types",
    tags=["notification-types"],
    include_in_schema=utils.get_include_in_schema(),
)


@router.get(
    "",
    response_model=list[interfaces.NotificationType],
    description="Get all notification types.",
)
async def get_notification_types_route(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Get all notification types.

    Args:
        db: Database session.
    """
    notification_types = await crud_get_notification_types(db=db)
    return notification_types
