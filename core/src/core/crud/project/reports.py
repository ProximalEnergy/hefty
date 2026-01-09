from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import noload, selectinload

from core import models
from core.db_query import DbQuery


def get_project_report_instances(
    *,
    project_id: UUID,
    is_visible: bool | None,
    report_type_ids: list[int] | None = None,
    deep: bool = False,
) -> DbQuery[models.ReportInstance, Literal[False]]:
    """TODO: add description.

    Args:
        project_id: TODO: describe.
        is_visible: TODO: describe.
        report_type_ids: TODO: describe.
        deep: TODO: describe.
    """
    stmt = select(models.ReportInstance)

    stmt = stmt.where(
        models.ReportInstance.project_id == project_id,
    )

    if is_visible is not None:
        stmt = stmt.where(models.ReportInstance.is_visible == is_visible)

    if report_type_ids is not None:
        stmt = stmt.where(models.ReportInstance.report_type_id.in_(report_type_ids))

    if deep:
        stmt = stmt.options(selectinload(models.ReportInstance.report_type))
    else:
        stmt = stmt.options(noload(models.ReportInstance.report_type))

    return DbQuery(query=stmt)
