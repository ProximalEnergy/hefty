from sqlalchemy.orm import Session

from core import models


def get_project_type(*, db: Session, project_type_id: int):
    """todo

    Args:
        db: TODO: describe.
        project_type_id: TODO: describe.
    """
    return (
        db.query(models.ProjectType)
        .filter(models.ProjectType.project_type_id == project_type_id)
        .first()
    )


def get_project_types(
    db: Session,
    *,
    project_type_ids: list[int] = [],
    name_short: str = "",
    name_long: str = "",
):
    """todo

    Args:
        db: TODO: describe.
        project_type_ids: TODO: describe.
        name_short: TODO: describe.
        name_long: TODO: describe.
    """
    query = db.query(models.ProjectType)

    if project_type_ids:
        query = query.filter(models.ProjectType.project_type_id.in_(project_type_ids))
    if name_short:
        query = query.filter(models.ProjectType.name_short == name_short)
    if name_long:
        query = query.filter(models.ProjectType.name_long == name_long)

    return query.all()
