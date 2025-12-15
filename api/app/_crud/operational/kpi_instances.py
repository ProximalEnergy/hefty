from uuid import UUID

from sqlalchemy.orm import Session, noload, selectinload

from core import models


def get_kpi_instances(
    db: Session,
    *,
    project_ids: list[UUID] | None = None,
    is_visible: bool | None,
    kpi_type_ids: list[int] | None = None,
    deep: bool = False,
):
    """todo

    Args:
        db: TODO: describe.
        project_ids: TODO: describe.
        is_visible: TODO: describe.
        kpi_type_ids: TODO: describe.
        deep: TODO: describe.
    """
    query = db.query(models.KPIInstance)
    if project_ids is not None:
        query = query.filter(models.KPIInstance.project_id.in_(project_ids))

    if is_visible is not None:
        query = query.filter(models.KPIInstance.is_visible == is_visible)

    if kpi_type_ids is not None:
        query = query.filter(models.KPIInstance.kpi_type_id.in_(kpi_type_ids))

    query.options(_get_kpi_instances_options(deep=deep))

    return query.all()


def _get_kpi_instances_options(*, deep: bool):
    """todo

    Args:
        deep: TODO: describe.
    """
    if deep:
        options = selectinload(models.KPIInstance.kpi_type)
    else:
        options = noload(models.KPIInstance.kpi_type)

    return options
