from typing import Literal
from uuid import UUID

from core.db_query import DbQuery
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from core import models


def get_report_instances(
    *,
    project_ids: list[UUID] | None = None,
    is_visible: bool | None,
    report_type_ids: list[int] | None = None,
    deep: bool = False,
) -> DbQuery[models.ReportInstance, Literal[False]]:
    """Build a query for report instances with optional filters.

    Args:
        project_ids: Optional project UUIDs to include.
        is_visible: Optional visibility filter.
        report_type_ids: Optional report type IDs to include.
        deep: Whether to eager-load related report_type.
    """
    query = select(models.ReportInstance)

    if project_ids is not None:
        query = query.where(models.ReportInstance.project_id.in_(project_ids))

    if is_visible is not None:
        query = query.where(models.ReportInstance.is_visible == is_visible)

    if report_type_ids is not None:
        query = query.where(models.ReportInstance.report_type_id.in_(report_type_ids))

    if deep:
        query = query.options(selectinload(models.ReportInstance.report_type))
    else:
        query = query.options(noload(models.ReportInstance.report_type))

    return DbQuery(query=query)


async def bulk_upsert_report_instances(
    *,
    db: AsyncSession,
    project_id: UUID,
    report_instances: list[dict[str, int | bool]],
    report_type_ids_to_delete: list[int] | None = None,
):
    """
    Bulk upsert report instances for a project.

    Args:
        db: Database session
        project_id: Project UUID
        report_instances: List of dicts with 'report_type_id' and 'is_visible'
        report_type_ids_to_delete: Optional list of report_type_ids to delete

    Returns:
        List of created/updated report instances
    """
    # Delete instances if specified
    if report_type_ids_to_delete:
        delete_stmt = delete(models.ReportInstance).where(
            models.ReportInstance.project_id == project_id,
            models.ReportInstance.report_type_id.in_(report_type_ids_to_delete),
        )
        await db.execute(delete_stmt)

    # Get existing report instances for this project
    existing_query = select(models.ReportInstance).where(
        models.ReportInstance.project_id == project_id
    )
    result = await db.execute(existing_query)
    existing_instances = result.scalars().all()

    # Create a map of existing instances by report_type_id
    existing_map = {
        instance.report_type_id: instance for instance in existing_instances
    }

    # Process each report instance
    updated_instances = []
    for instance_data in report_instances:
        report_type_id: int = instance_data["report_type_id"]
        is_visible: bool = bool(instance_data["is_visible"])

        if report_type_id in existing_map:
            # Update existing instance
            existing_instance = existing_map[report_type_id]
            existing_instance.is_visible = is_visible
            updated_instances.append(existing_instance)
        else:
            # Create new instance
            new_instance = models.ReportInstance(
                project_id=project_id,
                report_type_id=report_type_id,
                is_visible=is_visible,
            )
            db.add(new_instance)
            updated_instances.append(new_instance)

    await db.commit()

    # Refresh all instances to get updated data
    for instance in updated_instances:
        await db.refresh(instance)

    return updated_instances
