import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.user_projects import update_user_project_favorite
from app._crud.admin.user_projects import (
    update_user_projects as update_user_projects_crud,
)
from app._dependencies import authorization
from core import models

router = APIRouter(prefix="/user-projects", tags=["user-projects"])


@router.post(
    "/update-user-projects",
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def update_user_projects_route(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_ids: list[str],
    operational_project_ids: list[list[uuid.UUID]],
):
    """Update user-project associations in bulk.

    Args:
        db: Async database session.
        user_ids: User ids to update.
        operational_project_ids: Project id lists aligned with user ids.
    """
    await update_user_projects_crud(
        db=db,
        user_ids=user_ids,
        operational_project_ids=operational_project_ids,
    )


# TODO:  Make this route more secure
@router.get("/{user_id}")
async def get_user_projects(
    *,
    user_id: str,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Get all user projects with favorited status for a user.

    Args:
        user_id: User id to query.
        db: Async database session.
    """
    query = select(models.UserProject).where(models.UserProject.user_id == user_id)
    result = await db.execute(query)
    user_projects = result.scalars().all()
    return user_projects


# TODO:  Make this route more secure
@router.patch(
    "/{user_id}/projects/{project_id}/favorite",
    dependencies=[Depends(authorization.require_user_project)],
)
async def update_project_favorite(
    *,
    user_id: str,
    project_id: uuid.UUID,
    favorite_update: interfaces.UserProjectFavoriteUpdate,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Update the favorite status for a user's project.

    Args:
        user_id: User id to update.
        project_id: Project id to update.
        favorite_update: Favorite status payload.
        db: Async database session.
    """
    return await update_user_project_favorite(
        db=db,
        user_id=user_id,
        project_id=project_id,
        is_favorited=favorite_update.is_favorited,
    )
