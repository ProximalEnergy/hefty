from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.user_kpi_types import (
    get_user_favorited_kpi_types,
    update_user_kpi_type_favorite,
)
from app._dependencies.authentication import get_user

router = APIRouter(prefix="/user-kpi-types", tags=["user-kpi-types"])


@router.patch("/favorite")
async def update_kpi_type_favorite(
    *,
    favorite_update: interfaces.UserKPITypeFavoriteUpdate,
    user: Annotated[interfaces.UserAuthed, Depends(get_user)],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Update the is_favorited field for the authenticated user's kpi_type

    Args:
        favorite_update: Update data with kpi_type_id and is_favorited.
        user: Authenticated user data.
        db: Database session.
    """
    return await update_user_kpi_type_favorite(
        db=db,
        user_id=user.user_id,
        kpi_type_id=favorite_update.kpi_type_id,
        is_favorited=favorite_update.is_favorited,
    )


@router.get("/favorite")
async def get_user_favorited_kpi_types_route(
    *,
    user: Annotated[interfaces.UserAuthed, Depends(get_user)],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
) -> list[interfaces.UserKPITypes]:
    """Get all favorited KPI types for the authenticated user

    Args:
        user: Authenticated user data.
        db: Database session.
    """
    db_results = await get_user_favorited_kpi_types(db=db, user_id=user.user_id)
    return [
        interfaces.UserKPITypes(
            user_id=result.user_id,
            kpi_type_id=int(result.kpi_type_id),
            is_favorited=result.is_favorited,
        )
        for result in db_results
    ]
