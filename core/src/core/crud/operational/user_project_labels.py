import uuid
from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


def get_user_project_labels_by_user_id(
    *, user_id: str
) -> DbQuery[models.UserProjectLabel, Literal[False]]:
    """Build a query for all user project labels by user id.

    Args:
        user_id: User id to filter by.
    """
    upl = models.UserProjectLabel
    stmt = select(upl).where(upl.user_id == user_id)
    return DbQuery(query=stmt)


def get_user_project_labels_by_user_id_and_project_id(
    *, user_id: str, project_id: uuid.UUID
) -> DbQuery[models.UserProjectLabel, Literal[False]]:
    """Build a query for user project labels attached to a project.

    Args:
        user_id: User id to filter by.
        project_id: Project id to filter by.
    """
    upl = models.UserProjectLabel
    pl = models.ProjectLabel
    stmt = (
        select(upl)
        .join(pl, pl.user_project_label_id == upl.user_project_label_id)
        .where(
            upl.user_id == user_id,
            pl.project_id == project_id,
        )
    )
    return DbQuery(query=stmt)


def get_project_labels_by_user_project_label_ids(
    *, user_project_label_ids: list[int]
) -> DbQuery[models.ProjectLabel, Literal[False]]:
    """Build a query for project-label links for label IDs.

    Args:
        user_project_label_ids: User project label IDs to filter by.
    """
    stmt = select(models.ProjectLabel).where(
        models.ProjectLabel.user_project_label_id.in_(user_project_label_ids)
    )
    return DbQuery(query=stmt)


async def add_user_project_label(
    *,
    db: AsyncSession,
    user_id: str,
    name: str,
    color: str,
    project_ids: list[uuid.UUID],
) -> models.UserProjectLabel:
    """Create a user project label and attach it to projects.

    Args:
        db: Database session scoped to the operational schema.
        user_id: ID of the user creating the label.
        name: Label name.
        color: Label color (hex string).
        project_ids: Projects to associate with this label.
    """
    unique_project_ids = list(dict.fromkeys(project_ids))
    user_project_label = models.UserProjectLabel(
        user_id=user_id,
        name=name,
        color=color,
    )
    db.add(user_project_label)
    await db.flush()

    project_labels = [
        models.ProjectLabel(
            user_project_label_id=user_project_label.user_project_label_id,
            project_id=project_id,
        )
        for project_id in unique_project_ids
    ]
    db.add_all(project_labels)

    await db.commit()
    await db.refresh(user_project_label)
    return user_project_label


async def update_user_project_label(
    *,
    db: AsyncSession,
    user_id: str,
    user_project_label_id: int,
    name: str,
    color: str,
    project_ids: list[uuid.UUID],
) -> models.UserProjectLabel:
    """Update a user project label and re-attach projects.

    Args:
        db: Database session scoped to the operational schema.
        user_id: ID of the user who owns the label.
        user_project_label_id: Existing user project label id.
        name: New label name.
        color: New label color.
        project_ids: Projects to associate with this label.
    """
    label_query = select(models.UserProjectLabel).where(
        models.UserProjectLabel.user_id == user_id,
        models.UserProjectLabel.user_project_label_id == user_project_label_id,
    )
    label_result = await db.execute(label_query)
    user_project_label = label_result.scalar_one_or_none()

    if user_project_label is None:
        raise ValueError("User project label not found")

    user_project_label.name = name
    user_project_label.color = color

    await db.execute(
        delete(models.ProjectLabel).where(
            models.ProjectLabel.user_project_label_id
            == user_project_label.user_project_label_id
        )
    )

    unique_project_ids = list(dict.fromkeys(project_ids))
    project_labels = [
        models.ProjectLabel(
            user_project_label_id=user_project_label.user_project_label_id,
            project_id=project_id,
        )
        for project_id in unique_project_ids
    ]
    db.add_all(project_labels)

    await db.commit()
    await db.refresh(user_project_label)
    return user_project_label


async def delete_user_project_label(
    *,
    db: AsyncSession,
    user_id: str,
    user_project_label_id: int,
) -> bool:
    """Delete a user project label by user id and label id.

    Args:
        db: Database session scoped to the operational schema.
        user_id: ID of the user who owns the label.
        user_project_label_id: Label id to delete.
    """
    label_query = select(models.UserProjectLabel).where(
        models.UserProjectLabel.user_id == user_id,
        models.UserProjectLabel.user_project_label_id == user_project_label_id,
    )
    label_result = await db.execute(label_query)
    user_project_label = label_result.scalar_one_or_none()

    if user_project_label is None:
        return False

    await db.delete(user_project_label)
    await db.commit()
    return True
