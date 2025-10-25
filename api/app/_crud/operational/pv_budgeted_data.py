import datetime
import uuid

from sqlalchemy import and_, select
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
    from sqlalchemy import extract, or_

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
    This aggregates hourly data to daily values and applies degradation adjustment.

    Args:
        db: Database session
        project_id: UUID of the project
        pv_budgeted_series_id: Specific series ID to get data for
        start_date: Start date for the range
        end_date: End date for the range
        degradation_rate: Annual degradation rate percentage (default 0.5%)

    Returns:
        List of daily aggregated budgeted data
    """
    try:
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

        # Get data for this series with month/day filtering to reduce data size
        from sqlalchemy import extract, or_

        # Create month/day range conditions
        start_month = start_date.month
        start_day = start_date.day
        end_month = end_date.month
        end_day = end_date.day

        # Build month/day filter conditions
        month_day_conditions = []

        if start_month == end_month:
            # Same month, filter by day range
            month_day_conditions.append(
                and_(
                    extract("month", models.PVBudgetedData.time) == start_month,
                    extract("day", models.PVBudgetedData.time) >= start_day,
                    extract("day", models.PVBudgetedData.time) <= end_day,
                )
            )
        else:
            # Different months, need more complex logic
            # Start month: from start_day to end of month
            month_day_conditions.append(
                and_(
                    extract("month", models.PVBudgetedData.time) == start_month,
                    extract("day", models.PVBudgetedData.time) >= start_day,
                )
            )
            # End month: from start of month to end_day
            month_day_conditions.append(
                and_(
                    extract("month", models.PVBudgetedData.time) == end_month,
                    extract("day", models.PVBudgetedData.time) <= end_day,
                )
            )
            # Months in between (if any)
            for month in range(start_month + 1, end_month):
                month_day_conditions.append(
                    extract("month", models.PVBudgetedData.time) == month
                )

        data_query = (
            select(models.PVBudgetedData)
            .filter(
                models.PVBudgetedData.pv_budgeted_series_id == pv_budgeted_series_id
            )
            .filter(or_(*month_day_conditions))
            .order_by(models.PVBudgetedData.time)
            .limit(10000)  # Limit to prevent memory issues
        )

        result = await db.execute(data_query)
        all_data = result.scalars().all()

        if not all_data:
            return []

        # Process and aggregate data
        from collections import defaultdict

        # Group data by date (normalized to current year)
        daily_data = defaultdict(list)
        current_year = datetime.datetime.now().year

        for point in all_data:
            # Normalize the time to current year for display, handling leap year issues
            try:
                # Try to replace the year, but handle invalid dates (like Feb 29 in non-leap years)
                point_time = point.time.replace(year=current_year)
            except ValueError:
                # If the date is invalid (e.g., Feb 29 in non-leap year),
                # adjust to the closest valid date
                original_date = point.time.date()
                try:
                    # Try Feb 28 instead of Feb 29
                    adjusted_date = original_date.replace(month=2, day=28)
                    point_time = datetime.datetime.combine(
                        adjusted_date, point.time.time()
                    )
                    point_time = point_time.replace(year=current_year)
                except ValueError:
                    # If still invalid, use the original time
                    point_time = point.time

            # Check if this date falls within our range
            point_date = point_time.date()
            if start_date <= point_date <= end_date:
                daily_data[point_date].append(point)

        # Aggregate to daily values and apply degradation
        aggregated_data = []

        for date, hourly_points in daily_data.items():
            # Calculate years since project COD (if available)
            years_since_cod = 0
            # Note: We would need to join with Project table to get COD date
            # For now, we'll use 0 years since COD

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
        import logging

        logging.error(f"Error in get_pv_budgeted_series_daily_data: {e}")
        return []
