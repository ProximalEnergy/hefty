import uuid
from typing import Annotated

from core.crud.operational.user_project_labels import (
    add_user_project_label,
    get_project_labels_by_user_project_label_ids,
    get_user_project_labels_by_user_id,
)
from core.crud.operational.user_project_labels import (
    delete_user_project_label as delete_user_project_label_crud,
)
from core.crud.operational.user_project_labels import (
    update_user_project_label as update_user_project_label_crud,
)
from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app._dependencies.authentication import get_user
from app.dependencies import get_async_db
from app.interfaces import UserAuthed, UserProjectLabel
from core import models

router = APIRouter(prefix="/user-project-labels", tags=["user_project_labels"])


class UserProjectLabelCreate(BaseModel):
    """Payload for creating a user project label."""

    name: str = Field(min_length=1, max_length=64)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    project_ids: list[uuid.UUID] = Field(min_length=1)


def _normalize_label_name(*, label_name: str) -> str:
    """Normalize a label name and ensure it is non-empty.

    Args:
        label_name: Label name to normalize.
    """
    normalized_name = label_name.strip()
    if not normalized_name:
        raise HTTPException(status_code=422, detail="Label name cannot be blank")
    return normalized_name


def _validate_project_access(*, user: UserAuthed, project_ids: list[uuid.UUID]) -> None:
    """Validate that all requested projects are accessible by the user.

    Args:
        user: Authenticated user data.
        project_ids: Requested project IDs.
    """
    permitted_project_ids = set(user.operational_project_ids)
    requested_project_ids = set(project_ids)
    if not requested_project_ids.issubset(permitted_project_ids):
        raise HTTPException(
            status_code=403,
            detail="User does not have access to one or more selected projects",
        )


async def _build_user_project_labels(
    *,
    user_id: str,
    labels: list[models.UserProjectLabel],
) -> list[UserProjectLabel]:
    """Build a response payload for the given set of label models.

    Args:
        user_id: Requesting user id.
        labels: Label records for the requesting user.
    """
    if not labels:
        return []

    label_ids = [label.user_project_label_id for label in labels]
    project_links_query = get_project_labels_by_user_project_label_ids(
        user_project_label_ids=label_ids,
    )
    project_label_links = await project_links_query.get_async(
        output_type=OutputType.SQLALCHEMY
    )

    project_ids_by_label_id: dict[int, list[uuid.UUID]] = {}
    for project_label_link in project_label_links:
        project_ids_by_label_id.setdefault(
            project_label_link.user_project_label_id, []
        ).append(project_label_link.project_id)

    sorted_labels = sorted(labels, key=lambda label: label.name.lower())
    return [
        UserProjectLabel(
            user_project_label_id=label.user_project_label_id,
            user_id=user_id,
            name=label.name,
            color=label.color,
            project_ids=project_ids_by_label_id.get(label.user_project_label_id, []),
        )
        for label in sorted_labels
    ]


@router.get("", response_model=list[UserProjectLabel])
async def get_user_project_labels(
    user: Annotated[UserAuthed, Depends(get_user)],
):
    """Get project labels for the requesting user.

    Args:
        user: Authenticated user data.
    """
    labels_query = get_user_project_labels_by_user_id(user_id=user.user_id)

    labels = await labels_query.get_async(output_type=OutputType.SQLALCHEMY)
    return await _build_user_project_labels(
        user_id=user.user_id,
        labels=labels,
    )


@router.post("", response_model=UserProjectLabel)
async def create_user_project_label(
    user_project_label: UserProjectLabelCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[UserAuthed, Depends(get_user)],
):
    """Create a project label for the requesting user.

    Args:
        user_project_label: Project label payload.
        db: Database session.
        user: Authenticated user data.
    """
    normalized_name = _normalize_label_name(label_name=user_project_label.name)
    normalized_project_ids = list(dict.fromkeys(user_project_label.project_ids))
    _validate_project_access(user=user, project_ids=normalized_project_ids)

    try:
        created_label = await add_user_project_label(
            db=db,
            user_id=user.user_id,
            name=normalized_name,
            color=user_project_label.color,
            project_ids=normalized_project_ids,
        )
    except IntegrityError as err:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A project label with this name already exists",
        ) from err

    return UserProjectLabel(
        user_project_label_id=created_label.user_project_label_id,
        user_id=user.user_id,
        name=normalized_name,
        color=user_project_label.color,
        project_ids=normalized_project_ids,
    )


@router.put("/{user_project_label_id}", response_model=UserProjectLabel)
async def update_user_project_label(
    user_project_label_id: int,
    user_project_label: UserProjectLabelCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[UserAuthed, Depends(get_user)],
):
    """Update a project label for the requesting user.

    Args:
        user_project_label_id: Existing user project label id.
        user_project_label: Updated project label payload.
        db: Database session.
        user: Authenticated user data.
    """
    normalized_name = _normalize_label_name(label_name=user_project_label.name)
    normalized_project_ids = list(dict.fromkeys(user_project_label.project_ids))
    _validate_project_access(user=user, project_ids=normalized_project_ids)

    try:
        await update_user_project_label_crud(
            db=db,
            user_id=user.user_id,
            user_project_label_id=user_project_label_id,
            name=normalized_name,
            color=user_project_label.color,
            project_ids=normalized_project_ids,
        )
    except ValueError as err:
        raise HTTPException(status_code=404, detail="Project label not found") from err
    except IntegrityError as err:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A project label with this name already exists",
        ) from err

    return UserProjectLabel(
        user_project_label_id=user_project_label_id,
        user_id=user.user_id,
        name=normalized_name,
        color=user_project_label.color,
        project_ids=normalized_project_ids,
    )


@router.delete("/{user_project_label_id}", status_code=204)
async def delete_user_project_label(
    user_project_label_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    user: Annotated[UserAuthed, Depends(get_user)],
):
    """Delete a project label for the requesting user.

    Args:
        user_project_label_id: Label id to delete.
        db: Database session.
        user: Authenticated user data.
    """
    was_deleted = await delete_user_project_label_crud(
        db=db,
        user_id=user.user_id,
        user_project_label_id=user_project_label_id,
    )
    if not was_deleted:
        raise HTTPException(status_code=404, detail="Project label not found")
