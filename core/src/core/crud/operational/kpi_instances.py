from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from core import models
from core.db_query import DbQuery


def get_kpi_instances_for_matrix(
    *,
    project_ids: Iterable[UUID] | None = None,
    kpi_type_ids: Iterable[int] | None = None,
) -> DbQuery[models.KPIInstance]:
    """Return KPIInstance rows filtered by optional project or KPI IDs.

    Args:
        project_ids: Optional iterable of project IDs to filter by.
        kpi_type_ids: Optional iterable of KPI type IDs to filter by.
    """
    stmt = sa.select(models.KPIInstance)
    if project_ids is not None:
        stmt = stmt.where(models.KPIInstance.project_id.in_(list(project_ids)))
    if kpi_type_ids is not None:
        stmt = stmt.where(models.KPIInstance.kpi_type_id.in_(list(kpi_type_ids)))
    return DbQuery(query=stmt, is_scalar=False)


def bulk_upsert_kpi_instances(
    *,
    db: Session,
    rows: list[tuple[UUID, int, bool]],
) -> None:
    """Insert or update KPIInstance rows.

    Args:
        db: Database session.
        rows: List of ``(project_id, kpi_type_id, is_visible)`` tuples.
    """
    if not rows:
        return

    values = [
        {
            "project_id": project_id,
            "kpi_type_id": kpi_type_id,
            "is_visible": is_visible,
        }
        for project_id, kpi_type_id, is_visible in rows
    ]
    kpi_table = cast(Any, models.KPIInstance.__table__)
    stmt = insert(kpi_table).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["project_id", "kpi_type_id"],
        set_={"is_visible": stmt.excluded.is_visible},
    )
    db.execute(stmt)
    db.commit()


def bulk_delete_kpi_instances(
    *,
    db: Session,
    rows: list[tuple[UUID, int]],
) -> None:
    """Delete KPIInstance rows for the given (project_id, kpi_type_id) pairs.

    Args:
        db: Database session.
        rows: List of ``(project_id, kpi_type_id)`` tuples to delete.
    """
    if not rows:
        return

    project_kpi_pairs = [(project_id, kpi_type_id) for project_id, kpi_type_id in rows]
    stmt = sa.delete(models.KPIInstance).where(
        sa.tuple_(models.KPIInstance.project_id, models.KPIInstance.kpi_type_id).in_(
            project_kpi_pairs
        )
    )
    db.execute(stmt)
    db.commit()
