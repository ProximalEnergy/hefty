import datetime
import logging
import uuid
from collections import defaultdict

from sqlalchemy import and_, extract, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_pv_budgeted_data(
    *,
    db: AsyncSession,
    project_id: uuid.UUID,
    start: datetime.datetime,
    end: datetime.datetime,
    pv_budgeted_series_id: int | None = None,
):
    """
    Fetch PV budgeted data for a project within a time range.

    Args:
        db: Database session
        project_id: UUID of the project
        start: Start datetime
        end: End datetime
        pv_budgeted_series_id: Optional specific series ID to filter

    Returns:
        List of PVBudgetedData records
    """
    # First, get the series for this project
    series_query = select(models.PVBudgetedSeries).filter(
        models.PVBudgetedSeries.project_id == project_id,
    )

    if pv_budgeted_series_id is not None:
        series_query = series_query.filter(
            models.PVBudgetedSeries.pv_budgeted_series_id == pv_budgeted_series_id,
        )

    series_result = await db.execute(series_query)
    series_list = series_result.scalars().all()

    if not series_list:
        return []

    series_ids = [series.pv_budgeted_series_id for series in series_list]

    # Now get the data for these series
    # For budgeted data (especially TMY data), we need to match by month and day
    # rather than exact dates, since the data might be from year 2000 or other years

    # Extract month and day from the start and end dates
    start_month = start.month
    start_day = start.day
    end_month = end.month
    end_day = end.day

    # Create a condition that matches any year but the correct month/day range
    # This handles cases where budgeted data is from year 2000 or other years
    month_day_condition = or_(
        # Case 1: Start and end are in the same month
        and_(
            extract("month", models.PVBudgetedData.time) == start_month,
            extract("day", models.PVBudgetedData.time) >= start_day,
            extract("day", models.PVBudgetedData.time) < end_day,
        )
        if start_month == end_month
        # Case 2: Start and end span multiple months
        else or_(
            # Start month: from start_day to end of month
            and_(
                extract("month", models.PVBudgetedData.time) == start_month,
                extract("day", models.PVBudgetedData.time) >= start_day,
            ),
            # Middle months: all days
            and_(
                extract("month", models.PVBudgetedData.time) > start_month,
                extract("month", models.PVBudgetedData.time) < end_month,
            ),
            # End month: from start of month to end_day
            and_(
                extract("month", models.PVBudgetedData.time) == end_month,
                extract("day", models.PVBudgetedData.time) < end_day,
            ),
        )
    )

    data_query = (
        select(models.PVBudgetedData)
        .filter(
            and_(
                models.PVBudgetedData.pv_budgeted_series_id.in_(series_ids),
                month_day_condition,
            ),
        )
        .order_by(models.PVBudgetedData.time)
    )

    result = await db.execute(data_query)
    return result.scalars().all()


async def get_pv_budgeted_series(
    *,
    db: AsyncSession,
    project_id: uuid.UUID,
):
    """
    Get all budgeted series for a project.

    Args:
        db: Database session
        project_id: UUID of the project

    Returns:
        List of PVBudgetedSeries records
    """
    query = select(models.PVBudgetedSeries).filter(
        models.PVBudgetedSeries.project_id == project_id,
    )

    result = await db.execute(query)
    return result.scalars().all()


async def get_pv_budgeted_series_full_data(
    *,
    db: AsyncSession,
    project_id: uuid.UUID,
    pv_budgeted_series_id: int,
):
    """
    Get all budgeted data for a specific series (entire dataset).
    This is used for preloading the full series to the frontend.

    Args:
        db: Database session
        project_id: UUID of the project
        pv_budgeted_series_id: Specific series ID to get full data for

    Returns:
        List of PVBudgetedData records for the entire series
    """
    # First verify the series belongs to this project
    series_query = select(models.PVBudgetedSeries).filter(
        and_(
            models.PVBudgetedSeries.project_id == project_id,
            models.PVBudgetedSeries.pv_budgeted_series_id == pv_budgeted_series_id,
        )
    )

    series_result = await db.execute(series_query)
    series = series_result.scalar_one_or_none()

    if not series:
        return []

    # Get all data for this series
    data_query = (
        select(models.PVBudgetedData)
        .filter(models.PVBudgetedData.pv_budgeted_series_id == pv_budgeted_series_id)
        .order_by(models.PVBudgetedData.time)
    )

    result = await db.execute(data_query)
    return result.scalars().all()


async def get_pv_budgeted_series_daily_data(
    *,
    db: AsyncSession,
    project_id: uuid.UUID,
    pv_budgeted_series_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    degradation_rate: float = 0.5,
):
    """
    Get daily aggregated budgeted data for a specific series within a date range.
    This aggregates hourly data to daily values and applies degradation adjustment
    based on the project's Commercial Operation Date (COD).

    The budgeted data is from 2019 (one full year), and this function maps any requested
    date to the corresponding date in 2019, handling year-over-year ranges properly.
    Degradation is calculated as years since COD * degradation_rate.

    Args:
        db: Database session
        project_id: UUID of the project
        pv_budgeted_series_id: Specific series ID to get data for
        start_date: Start date for the range
        end_date: End date for the range
        degradation_rate: Annual degradation rate percentage (default 0.5%)

    Returns:
        List of daily aggregated budgeted data with proper degradation applied
    """
    try:
        # First verify the series belongs to this project and get the COD date
        series_query = (
            select(models.PVBudgetedSeries, models.Project.cod)
            .join(
                models.Project,
                models.PVBudgetedSeries.project_id == models.Project.project_id,
            )
            .filter(
                and_(
                    models.PVBudgetedSeries.project_id == project_id,
                    models.PVBudgetedSeries.pv_budgeted_series_id
                    == pv_budgeted_series_id,
                )
            )
        )

        series_result = await db.execute(series_query)
        series_data = series_result.first()

        if not series_data:
            return []

        series, cod_date = series_data

        # Get ALL budgeted data for this series (it's only one year from 2019)
        # We'll filter and map it in Python to handle year-over-year ranges properly
        data_query = (
            select(models.PVBudgetedData)
            .filter(
                models.PVBudgetedData.pv_budgeted_series_id == pv_budgeted_series_id
            )
            .order_by(models.PVBudgetedData.time)
        )

        result = await db.execute(data_query)
        all_data = result.scalars().all()

        if not all_data:
            return []

        # Process and aggregate data
        # Group budgeted data by month-day (from 2019)
        budgeted_data_by_month_day = defaultdict(list)

        for point in all_data:
            # Group by month-day from the budgeted data (2019)
            month_day_key = (point.time.month, point.time.day)
            budgeted_data_by_month_day[month_day_key].append(point)

        # Now map requested dates to budgeted data
        daily_data = defaultdict(list)

        # Generate all dates in the requested range
        current_date = start_date
        while current_date <= end_date:
            # Map this date to the corresponding date in 2019 budgeted data
            month_day_key = (current_date.month, current_date.day)

            if month_day_key in budgeted_data_by_month_day:
                # Use the budgeted data for this month-day
                daily_data[current_date] = budgeted_data_by_month_day[month_day_key]

            current_date += datetime.timedelta(days=1)

        # Aggregate to daily values and apply degradation
        aggregated_data = []

        for date, hourly_points in daily_data.items():
            # Calculate years since project COD
            years_since_cod = 0
            if cod_date:
                # Calculate the difference between the current date and COD
                # Use the year of the current date for calculation
                current_year_date = datetime.date(date.year, date.month, date.day)
                years_since_cod = (current_year_date - cod_date).days / 365.25

            # Apply degradation factor
            degradation_factor = (1 - degradation_rate / 100) ** years_since_cod

            # Sum hourly AC power to get daily energy (MWh)
            daily_energy = sum(
                point.poi_ac_power * degradation_factor for point in hourly_points
            )

            # Calculate average values for other metrics
            avg_ghi = (
                sum(p.ghi for p in hourly_points if p.ghi is not None)
                / len([p for p in hourly_points if p.ghi is not None])
                if any(p.ghi is not None for p in hourly_points)
                else None
            )
            avg_poa = sum(p.poa for p in hourly_points) / len(hourly_points)
            avg_temperature = (
                sum(p.temperature for p in hourly_points if p.temperature is not None)
                / len([p for p in hourly_points if p.temperature is not None])
                if any(p.temperature is not None for p in hourly_points)
                else None
            )
            avg_soiling = (
                sum(
                    p.soiling_percentage
                    for p in hourly_points
                    if p.soiling_percentage is not None
                )
                / len([p for p in hourly_points if p.soiling_percentage is not None])
                if any(p.soiling_percentage is not None for p in hourly_points)
                else None
            )

            aggregated_data.append(
                {
                    "date": date.isoformat(),
                    "daily_energy_mwh": round(daily_energy, 4),
                    "avg_ghi": round(avg_ghi, 2) if avg_ghi is not None else None,
                    "avg_poa": round(avg_poa, 2),
                    "avg_temperature": round(avg_temperature, 2)
                    if avg_temperature is not None
                    else None,
                    "avg_soiling_percentage": round(avg_soiling, 2)
                    if avg_soiling is not None
                    else None,
                    "degradation_factor": round(degradation_factor, 6),
                    "years_since_cod": round(years_since_cod, 2),
                }
            )

        # Sort by date
        aggregated_data.sort(key=lambda x: str(x["date"]))

        return aggregated_data

    except Exception as e:
        # Log the error and return empty list to prevent API crashes
        logging.error(f"Error in get_pv_budgeted_series_daily_data: {e}")
        return []
