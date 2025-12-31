from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models


def get_project_type(*, db: Session, project_type_id: int):
    """Return a project type by its primary key.

    Args:
        db: Database session used to run the lookup.
        project_type_id: Identifier of the project type to retrieve.
    """
    query = select(models.ProjectType).where(
        models.ProjectType.project_type_id == project_type_id,
    )
    return db.execute(query).scalars().first()


def get_project_types(
    *,
    db: Session,
    project_type_ids: list[int] = [],
    name_short: str = "",
    name_long: str = "",
):
    """List project types filtered by identifiers or names.

    Args:
        db: Database session used to run the query.
        project_type_ids: Optional identifiers to match.
        name_short: Short name that must match exactly when provided.
        name_long: Long name that must match exactly when provided.
    """
    query = select(models.ProjectType)

    if project_type_ids:
        query = query.where(models.ProjectType.project_type_id.in_(project_type_ids))
    if name_short:
        query = query.where(models.ProjectType.name_short == name_short)
    if name_long:
        query = query.where(models.ProjectType.name_long == name_long)

    return db.execute(query).scalars().all()
