from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.users import get_user as crud_get_user

router = APIRouter(prefix="/report-preferences", tags=["report-preferences"])


@router.get("", deprecated=True)
async def get_report_preferences(
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """todo

    Args:
        user_data: TODO: describe.
        db: TODO: describe.
    """
    user = await crud_get_user(db=db, user_id=user_data.user_id)

    return user.subscribed_to_reports  # pyright: ignore


@router.put("", deprecated=True)
async def update_report_preferences(
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """todo

    Args:
        user_data: TODO: describe.
        db: TODO: describe.
    """
    await crud_get_user(db=db, user_id=user_data.user_id)

    # crud.update_user_report_preferences(
    #     db, user.user_id, not user.subscribed_to_reports
    # )
    return 400
