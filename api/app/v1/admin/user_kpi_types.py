from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.user_kpi_types import (
    get_user_favorited_kpi_types,
    update_user_kpi_type_favorite,
)

router = APIRouter(prefix="/user-kpi-types", tags=["user-kpi-types"])


@router.patch("/favorite")
async def update_kpi_type_favorite(
    *,
    favorite_update: interfaces.UserKPITypes,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Update the is_favorited field for a user's kpi_type

    Args:
        favorite_update: TODO: describe.
        db: TODO: describe.
    """
    return await update_user_kpi_type_favorite(
        db=db,
        user_id=favorite_update.user_id,
        kpi_type_id=favorite_update.kpi_type_id,
        is_favorited=favorite_update.is_favorited,
    )


@router.get("/favorite")
async def get_user_favorited_kpi_types_route(
    *,
    user_id: str,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
) -> list[interfaces.UserKPITypes]:
    """Get all favorited KPI types for a given user

    Args:
        user_id: TODO: describe.
        db: TODO: describe.
    """
    db_results = await get_user_favorited_kpi_types(db=db, user_id=user_id)
    return [
        interfaces.UserKPITypes(
            user_id=result.user_id,
            kpi_type_id=int(result.kpi_type_id),
            is_favorited=result.is_favorited,
        )
        for result in db_results
    ]
