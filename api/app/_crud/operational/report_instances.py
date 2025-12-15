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
    """todo

    Args:
        db: TODO: describe.
        project_ids: TODO: describe.
        is_visible: TODO: describe.
        report_type_ids: TODO: describe.
        deep: TODO: describe.
    """
    query = select(models.ReportInstance)
    if project_ids is not None:
        query = query.where(models.ReportInstance.project_id.in_(project_ids))

    if is_visible is not None:
        query = query.where(models.ReportInstance.is_visible == is_visible)

    if report_type_ids is not None:
        query = query.where(models.ReportInstance.report_type_id.in_(report_type_ids))

    query = query.options(_get_report_instances_options(deep=deep))

    return (await db.execute(query)).scalars().all()


async def bulk_upsert_report_instances(
    *,
    db: AsyncSession,
    project_id: UUID,
    report_instances: list[dict[str, int | bool]],
):
    """
    Bulk upsert report instances for a project.

    Args:
        db: Database session
        project_id: Project UUID
        report_instances: List of dicts with 'report_type_id' and 'is_visible'

    Returns:
        List of created/updated report instances
    """
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


def _get_report_instances_options(*, deep: bool):
    """todo

    Args:
        deep: TODO: describe.
    """
    if deep:
        options = selectinload(models.ReportInstance.report_type)
    else:
        options = noload(models.ReportInstance.report_type)

    return options
