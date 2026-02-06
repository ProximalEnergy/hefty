import datetime
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app import interfaces
from core import enumerations, models


def create_series(
    *,
    project_db: Session,
    series_in: interfaces.PVBudgetedSeriesIn,
    company_id: uuid.UUID,
    project_id: uuid.UUID,
) -> models.PVBudgetedSeries:
    """Create a PV budgeted series for a project.

    Args:
        project_db: Project database session.
        series_in: Series payload describing PV budgeted settings.
        company_id: Company identifier owning the series.
        project_id: Project identifier for the series.
    """
    series = models.PVBudgetedSeries(
        company_id=company_id,
        project_id=project_id,
        p_value=series_in.p_value,
        frequency=series_in.frequency,
        soiling_mode=(
            enumerations.PVBudgetedSoilingMode(series_in.soiling_mode)
            if series_in.soiling_mode is not None
            else None
        ),
        soiling_fixed_percentage=series_in.soiling_fixed_percentage,
        tmy_source=series_in.tmy_source,
        model_version=series_in.model_version,
        filename=series_in.filename,
    )
    project_db.add(series)
    project_db.commit()
    project_db.refresh(series)
    return series


def list_series(
    *, project_db: Session, project_id: uuid.UUID | None = None
) -> Sequence[models.PVBudgetedSeries]:
    """List PV budgeted series, optionally filtered by project.

    Args:
        project_db: Project database session.
        project_id: Optional project identifier filter.
    """
    stmt = sa.select(models.PVBudgetedSeries)
    if project_id is not None:
        stmt = stmt.where(models.PVBudgetedSeries.project_id == project_id)
    stmt = stmt.order_by(models.PVBudgetedSeries.pv_budgeted_series_id.desc())
    result = project_db.execute(stmt)
    return result.scalars().all()


def get_series(
    *, project_db: Session, pv_budgeted_series_id: int
) -> models.PVBudgetedSeries | None:
    """Fetch a PV budgeted series by ID.

    Args:
        project_db: Project database session.
        pv_budgeted_series_id: Series identifier to fetch.
    """
    stmt = sa.select(models.PVBudgetedSeries).where(
        models.PVBudgetedSeries.pv_budgeted_series_id == pv_budgeted_series_id
    )
    result = project_db.execute(stmt)
    return result.scalar_one_or_none()


def update_series(
    *,
    project_db: Session,
    pv_budgeted_series_id: int,
    series_in: interfaces.PVBudgetedSeriesIn,
) -> models.PVBudgetedSeries | None:
    """Update a PV budgeted series by ID.

    Args:
        project_db: Project database session.
        pv_budgeted_series_id: Series identifier to update.
        series_in: Series payload with updated values.
    """
    stmt = sa.select(models.PVBudgetedSeries).where(
        models.PVBudgetedSeries.pv_budgeted_series_id == pv_budgeted_series_id
    )
    result = project_db.execute(stmt)
    series = result.scalar_one_or_none()
    if series is None:
        return None

    series.p_value = series_in.p_value
    series.frequency = series_in.frequency
    series.soiling_mode = (
        enumerations.PVBudgetedSoilingMode(series_in.soiling_mode)
        if series_in.soiling_mode is not None
        else None
    )
    series.soiling_fixed_percentage = series_in.soiling_fixed_percentage
    series.tmy_source = series_in.tmy_source
    series.model_version = series_in.model_version
    series.filename = series_in.filename

    project_db.add(series)
    project_db.commit()
    project_db.refresh(series)
    return series


def bulk_upsert_data(
    *,
    project_db: Session,
    pv_budgeted_series_id: int,
    rows: list[interfaces.PVBudgetedDataRow],
) -> int:
    """Upsert PV budgeted data rows for a series.

    Args:
        project_db: Project database session.
        pv_budgeted_series_id: Series identifier to update.
        rows: Data rows to insert or update.
    """
    if not rows:
        return 0

    # Use INSERT ... ON CONFLICT to upsert on (pv_budgeted_series_id, time)
    table = models.PVBudgetedData.__table__

    # Prepare data, ensuring timestamp is timezone-aware
    values = [
        dict(
            pv_budgeted_series_id=pv_budgeted_series_id,
            time=row.time_stamp,
            poi_ac_power=row.poi_ac_power,
            ghi=row.ghi,
            poa=row.poa,
            temperature=row.temperature,
            soiling_percentage=row.soiling_percentage,
        )
        for row in rows
    ]

    insert_stmt = pg_insert(table).values(values)  # type: ignore[arg-type]

    update_cols = {
        "poi_ac_power": insert_stmt.excluded.poi_ac_power,
        "ghi": insert_stmt.excluded.ghi,
        "poa": insert_stmt.excluded.poa,
        "temperature": insert_stmt.excluded.temperature,
        "soiling_percentage": insert_stmt.excluded.soiling_percentage,
    }
    on_conflict_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[
            table.c.pv_budgeted_series_id,
            table.c.time,
        ],
        set_=update_cols,
    )
    result = project_db.execute(on_conflict_stmt)
    project_db.commit()
    return result.rowcount or 0  # type: ignore


def delete_series(*, project_db: Session, pv_budgeted_series_id: int) -> bool:
    """Delete a PV budgeted series and its data rows.

    Args:
        project_db: Project database session.
        pv_budgeted_series_id: Series identifier to delete.
    """
    try:
        # First delete all associated data points
        data_stmt = sa.delete(models.PVBudgetedData).where(
            models.PVBudgetedData.pv_budgeted_series_id == pv_budgeted_series_id
        )
        project_db.execute(data_stmt)

        # Then delete the series itself
        series_stmt = sa.delete(models.PVBudgetedSeries).where(
            models.PVBudgetedSeries.pv_budgeted_series_id == pv_budgeted_series_id
        )
        series_result = project_db.execute(series_stmt)

        # Commit both deletions together
        project_db.commit()

        return series_result.rowcount > 0  # type: ignore
    except Exception as e:
        # Rollback on any error
        project_db.rollback()
        raise e


def fetch_data(
    *,
    project_db: Session,
    pv_budgeted_series_id: int,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> Sequence[models.PVBudgetedData]:
    """Fetch PV budgeted data for a series and time range.

    Args:
        project_db: Project database session.
        pv_budgeted_series_id: Series identifier to query.
        start: Inclusive start timezone-aware datetime for filtering data.
        end: Exclusive end timezone-aware datetime for filtering data.
    """
    stmt = sa.select(models.PVBudgetedData).where(
        models.PVBudgetedData.pv_budgeted_series_id == pv_budgeted_series_id
    )
    if start is not None:
        stmt = stmt.where(models.PVBudgetedData.time >= start)
    if end is not None:
        stmt = stmt.where(models.PVBudgetedData.time < end)
    stmt = stmt.order_by(models.PVBudgetedData.time)
    result = project_db.execute(stmt)
    return result.scalars().all()
