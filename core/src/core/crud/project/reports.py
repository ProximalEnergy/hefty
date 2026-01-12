from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload, noload

from core import models
from core.db_query import DbQuery


def get_project_report_instances(
    *,
    project_id: UUID,
    is_visible: bool | None,
    report_type_ids: list[int] | None = None,
    deep: bool = False,
) -> DbQuery[models.ReportInstance, Literal[False]]:
    """Build a query for report instances for a project.

    Args:
        project_id: Project UUID to filter report instances.
        is_visible: Optional visibility filter.
        report_type_ids: Optional list of report type ids to include.
        deep: Whether to eager-load report type relationships.
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
        stmt = stmt.options(joinedload(models.ReportInstance.report_type))
    else:
        stmt = stmt.options(noload(models.ReportInstance.report_type))

    return DbQuery(query=stmt)
