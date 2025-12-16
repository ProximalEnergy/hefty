from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, noload, selectinload

from core import models
from core.model_list import ModelList


def get_project_report_instances(
    db: Session,
    *,
    project_id: UUID,
    is_visible: bool | None,
    report_type_ids: list[int] | None = None,
    deep: bool = False,
    return_query: bool = False,
) -> ModelList[models.ReportInstance]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        project_id: TODO: describe.
        is_visible: TODO: describe.
        report_type_ids: TODO: describe.
        deep: TODO: describe.
        return_query: TODO: describe.
    """
    query = db.query(models.ReportInstance).filter(
        models.ReportInstance.project_id == project_id,
    )

    if is_visible is not None:
        query = query.filter(models.ReportInstance.is_visible == is_visible)

    if report_type_ids is not None:
        query = query.filter(models.ReportInstance.report_type_id.in_(report_type_ids))

    query.options(_get_project_report_instances_options(deep=deep))

    return ModelList(query=query, return_query=return_query)


def _get_project_report_instances_options(*, deep: bool) -> Any:
    """TODO: add description.

    Args:
        deep: TODO: describe.
    """
    if deep:
        options = selectinload(models.ReportInstance.report_type_id)
    else:
        options = noload(models.ReportInstance.report_type_id)

    return options
