from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from core import models


async def get_report_instances(
    *,
    db: AsyncSession,
    project_ids: list[UUID] | None = None,
    is_visible: bool | None,
    report_type_ids: list[int] | None = None,
    deep: bool = False,
):
    query = select(models.ReportInstance)
    if project_ids is not None:
        query = query.where(models.ReportInstance.project_id.in_(project_ids))

    if is_visible is not None:
        query = query.where(models.ReportInstance.is_visible == is_visible)

    if report_type_ids is not None:
        query = query.where(models.ReportInstance.report_type_id.in_(report_type_ids))

    query = query.options(_get_report_instances_options(deep=deep))

    return (await db.execute(query)).scalars().all()


def _get_report_instances_options(*, deep: bool):
    if deep:
        options = selectinload(models.ReportInstance.report_type)
    else:
        options = noload(models.ReportInstance.report_type)

    return options
