import datetime
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies
from app._crud.operational.pv_budgeted_data import (
    get_pv_budgeted_data as crud_get_pv_budgeted_data,
)
from app._crud.operational.pv_budgeted_data import (
    get_pv_budgeted_series as crud_get_pv_budgeted_series,
)
from app._crud.operational.pv_budgeted_data import (
    get_pv_budgeted_series_daily_data as crud_get_pv_budgeted_series_daily_data,
)
from app._dependencies.authorization import require_user_company

router = APIRouter(prefix="/pv-budgeted-data", tags=["pv_budgeted_data"])


@router.get(
    "/series",
    operation_id="get_pv_budgeted_series",
    dependencies=[Depends(require_user_company)],
)
async def get_pv_budgeted_series(
    *,
    project_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """Get all budgeted series for a project.

    Args:
        project_id: Description for project_id.
        db: Description for db.
    """
    return await crud_get_pv_budgeted_series(
        db=db,
        project_id=project_id,
    )


@router.get(
    "",
    operation_id="get_pv_budgeted_data",
    dependencies=[Depends(require_user_company)],
)
async def get_pv_budgeted_data(
    *,
    project_id: uuid.UUID,
    start: datetime.datetime,
    end: datetime.datetime,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """
    Get PV budgeted data for a project (all series).

    Args:
        project_id: UUID of the project
        start: Start datetime
        end: End datetime
        db: Database session
    """
    return await crud_get_pv_budgeted_data(
        db=db,
        project_id=project_id,
        start=start,
        end=end,
        pv_budgeted_series_id=None,
    )


@router.get(
    "/series/{pv_budgeted_series_id}",
    operation_id="get_pv_budgeted_data_by_series",
    dependencies=[Depends(require_user_company)],
)
async def get_pv_budgeted_data_by_series(
    *,
    project_id: uuid.UUID,
    start: datetime.datetime,
    end: datetime.datetime,
    pv_budgeted_series_id: int,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """
    Get PV budgeted data for a specific series.

    Args:
        project_id: UUID of the project
        start: Start datetime
        end: End datetime
        pv_budgeted_series_id: Specific series ID
        db: Database session
    """
    return await crud_get_pv_budgeted_data(
        db=db,
        project_id=project_id,
        start=start,
        end=end,
        pv_budgeted_series_id=pv_budgeted_series_id,
    )


@router.get(
    "/series/{pv_budgeted_series_id}/daily-data",
    operation_id="get_pv_budgeted_series_daily_data",
    dependencies=[Depends(require_user_company)],
)
async def get_pv_budgeted_series_daily_data(
    *,
    project_id: uuid.UUID,
    pv_budgeted_series_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    degradation_rate: float = 0.5,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """
    Get daily aggregated budgeted data for a specific series within a date range.
    This aggregates hourly data to daily values and applies degradation adjustment.

    Args:
        project_id: UUID of the project
        pv_budgeted_series_id: Specific series ID to get data for
        start_date: Start date for the range
        end_date: End date for the range
        degradation_rate: Annual degradation rate percentage (default 0.5%)
        db: Database session
    """
    return await crud_get_pv_budgeted_series_daily_data(
        db=db,
        project_id=project_id,
        pv_budgeted_series_id=pv_budgeted_series_id,
        start_date=start_date,
        end_date=end_date,
        degradation_rate=degradation_rate,
    )
