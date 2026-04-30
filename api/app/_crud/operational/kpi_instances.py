from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, noload, selectinload

from core import models


def api_get_kpi_instances(
    *,
    db: Session,
    project_ids: list[UUID] | None = None,
    is_visible: bool | None,
    kpi_type_ids: list[int] | None = None,
    deep: bool = False,
):
    """todo

    Args:
        db: Description for db.
        project_ids: Description for project_ids.
        is_visible: Description for is_visible.
        kpi_type_ids: Description for kpi_type_ids.
        deep: Description for deep.
    """
    statement = select(models.KPIInstance).options(
        _get_kpi_instances_options(deep=deep),
    )
    if project_ids is not None:
        statement = statement.where(
            models.KPIInstance.project_id.in_(project_ids),
        )

    if is_visible is not None:
        statement = statement.where(models.KPIInstance.is_visible == is_visible)

    if kpi_type_ids is not None:
        statement = statement.where(models.KPIInstance.kpi_type_id.in_(kpi_type_ids))

    return db.execute(statement).scalars().all()


def _get_kpi_instances_options(*, deep: bool):
    """todo

    Args:
        deep: Description for deep.
    """
    if deep:
        options = selectinload(models.KPIInstance.kpi_type)
    else:
        options = noload(models.KPIInstance.kpi_type)

    return options


async def bulk_upsert_kpi_instances_with_async_session(
    *,
    db: AsyncSession,
    rows: list[tuple[int, UUID, bool]],
) -> int:
    """Bulk upsert KPI instances.

    Args:
        db: Async database session.
        rows: Tuples of (kpi_type_id, project_id, is_visible).
    """
    if not rows:
        return 0

    table = models.KPIInstance.__table__
    values = [
        {
            "kpi_type_id": kpi_type_id,
            "project_id": project_id,
            "is_visible": is_visible,
        }
        for kpi_type_id, project_id, is_visible in rows
    ]

    insert_stmt = pg_insert(table).values(values)  # type: ignore[arg-type]
    on_conflict_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[
            table.c.project_id,
            table.c.kpi_type_id,
        ],
        set_={"is_visible": insert_stmt.excluded.is_visible},
    )
    result = await db.execute(on_conflict_stmt)
    return int(cast(Any, result).rowcount or 0)


async def bulk_delete_kpi_instances_with_async_session(
    *,
    db: AsyncSession,
    keys: list[tuple[int, UUID]],
) -> int:
    """Bulk delete KPI instances by composite key tuple.

    Args:
        db: Async database session.
        keys: Tuples of (kpi_type_id, project_id).
    """
    if not keys:
        return 0

    delete_stmt = delete(models.KPIInstance).where(
        tuple_(
            models.KPIInstance.kpi_type_id,
            models.KPIInstance.project_id,
        ).in_(keys)
    )
    result = await db.execute(delete_stmt)
    return int(cast(Any, result).rowcount or 0)
