"""
KPI Data CRUD Operations.

⚠️ IMPORTANT: NaN Handling
All aggregation functions in this module explicitly filter out NaN values
to prevent contamination of results. PostgreSQL treats NaN differently from
IEEE 754 standard (NaN = NaN returns TRUE), requiring special handling via
BETWEEN -Infinity AND Infinity filters.
"""

import datetime
from typing import Literal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import func, select

from core import models
from core.db_query import DbQuery
from core.enumerations import KPIType


def get_project_kpi_data_agg_freq(
    *,
    project_id: UUID,
    kpi_type_id: KPIType,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    frequency: Literal["month", "year"] | None = None,
    aggregation_method: Literal["sum", "avg"],
) -> sa.Select:
    """
    Build a query to retrieve aggregated KPI data with optional frequency binning.

    This function returns a SQLAlchemy Select object that can be executed by the
    caller. It automatically filters out NULL, NaN, and infinity values to ensure
    clean aggregations.

    Args:
        project_id: Project UUID to filter KPI data.
        kpi_type_id: KPI type to filter data.
        start: Optional start date filter (inclusive). If None, no start bound.
        end: Optional end date filter (exclusive). If None, no end bound.
        frequency: Optional aggregation bucket size ("month" or "year").
            When None, returns raw daily values without aggregation.
        aggregation_method: Aggregation to apply ("sum" or "avg").

    Returns:
        SQLAlchemy Select object that returns rows with 'date' and 'project_data'
        columns. Must be executed with a database session.

    Example:
        >>> query = get_project_kpi_data_agg_freq(
        ...     project_id=project_uuid,
        ...     kpi_type_id=KPIType.AVAILABILITY,
        ...     start=date(2025, 1, 1),
        ...     end=date(2025, 12, 31),
        ...     frequency="month",
        ...     aggregation_method="avg"
        ... )
        >>> async with db_session() as db:
        ...     result = await db.execute(query)
        ...     rows = result.mappings().all()
    """
    if frequency is None:
        query = select(
            models.OperationalKPIData.date.label(models.OperationalKPIData.date.name),
            models.OperationalKPIData.project_data.label(
                models.OperationalKPIData.project_data.name
            ),
        )
        period = None
    else:
        period = sa.cast(
            func.date_trunc(frequency, models.OperationalKPIData.date),
            sa.Date,
        ).label(models.OperationalKPIData.date.name)
        query = select(
            period,
            getattr(func, aggregation_method)(
                models.OperationalKPIData.project_data,
            ).label(models.OperationalKPIData.project_data.name),
        )

    query = query.where(models.OperationalKPIData.project_id == project_id)
    query = query.where(models.OperationalKPIData.kpi_type_id == kpi_type_id)
    if start:
        query = query.where(models.OperationalKPIData.date >= start)
    if end:
        query = query.where(models.OperationalKPIData.date < end)

    # ⚠️ CRITICAL: Special handling for NaN values in PostgreSQL
    # NaN values pollute aggregations (e.g., AVG with any NaN = NaN result).
    # We must explicitly exclude them before aggregation.
    #
    # PostgreSQL NaN behavior differs from IEEE 754:
    # - In IEEE 754: NaN != NaN (comparison returns false)
    # - In PostgreSQL: NaN = NaN (comparison returns TRUE)
    #
    # Therefore, approaches like `column = column` or `column != 'NaN'` do NOT work.
    # PostgreSQL also has no isnan() function in standard installations.
    #
    # Solution: Use BETWEEN -Infinity AND Infinity
    # - Normal numbers: included (e.g., -100 to 100)
    # - NaN: excluded (NaN is NOT between -Inf and Inf in PostgreSQL)
    # - ±Infinity: also excluded as a bonus
    query = query.where(models.OperationalKPIData.project_data.isnot(None))
    query = query.where(
        models.OperationalKPIData.project_data.between(
            float("-inf"), float("inf"), symmetric=False
        )
    )

    if frequency is None:
        query = query.order_by(models.OperationalKPIData.date)
    else:
        query = query.group_by(period).order_by(period)

    return query


def get_project_kpi_data_agg(
    *,
    project_id: UUID,
    kpi_type_id: KPIType,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    aggregation_method: Literal["sum", "avg"],
) -> DbQuery[float, Literal[True]]:
    """
    Build a query to aggregate KPI data into a single value across entire date range.

    This function returns a SQLAlchemy Select object that produces a single
    aggregated value (no date binning). It automatically filters out NULL, NaN,
    and infinity values to ensure clean aggregations.

    Args:
        project_id: Project UUID to filter KPI data.
        kpi_type_id: KPI type to filter data.
        start: Optional start date filter (inclusive). If None, no start bound.
        end: Optional end date filter (exclusive). If None, no end bound.
        aggregation_method: Aggregation to apply ("sum" or "avg").

    Returns:
        DbQuery that returns a single aggregated float value.

    Example:
        >>> query = get_project_kpi_data_agg(
        ...     project_id=project_uuid,
        ...     kpi_type_id=KPIType.AVAILABILITY,
        ...     start=date(2025, 1, 1),
        ...     end=date(2025, 12, 31),
        ...     aggregation_method="avg"
        ... )
        >>> avg_value = await query.get_async(output_type=OutputType.SQLALCHEMY)
    """

    query = select(
        getattr(func, aggregation_method)(models.OperationalKPIData.project_data).label(
            models.OperationalKPIData.project_data.name,
        ),
    )

    query = query.where(models.OperationalKPIData.project_id == project_id)
    query = query.where(models.OperationalKPIData.kpi_type_id == kpi_type_id)
    if start:
        query = query.where(models.OperationalKPIData.date >= start)
    if end:
        query = query.where(models.OperationalKPIData.date < end)

    # ⚠️ CRITICAL: Special handling for NaN values in PostgreSQL
    # NaN values pollute aggregations (e.g., AVG with any NaN = NaN result).
    # We must explicitly exclude them before aggregation.
    #
    # PostgreSQL NaN behavior differs from IEEE 754:
    # - In IEEE 754: NaN != NaN (comparison returns false)
    # - In PostgreSQL: NaN = NaN (comparison returns TRUE)
    #
    # Therefore, approaches like `column = column` or `column != 'NaN'` do NOT work.
    # PostgreSQL also has no isnan() function in standard installations.
    #
    # Solution: Use BETWEEN -Infinity AND Infinity
    # - Normal numbers: included (e.g., -100 to 100)
    # - NaN: excluded (NaN is NOT between -Inf and Inf in PostgreSQL)
    # - ±Infinity: also excluded as a bonus
    query = query.where(models.OperationalKPIData.project_data.isnot(None))
    query = query.where(
        models.OperationalKPIData.project_data.between(
            float("-inf"), float("inf"), symmetric=False
        )
    )

    return DbQuery(query=query, is_scalar=True)


def core_get_kpi_data(
    *,
    kpi_type_ids: list[int],
    start: datetime.date,
    end: datetime.date,
    project_ids: list[UUID] = [],
    include_device_data: bool = True,
) -> DbQuery[models.OperationalKPIData, Literal[False]]:
    """
    Get KPI data for a given project and date range.

    Args:
        kpi_type_ids: List of KPI type IDs to query.
        start: Start date.
        end: End date.
        project_ids: List of project IDs to query.
        include_device_data: Whether to include device data.
    """
    columns = list(models.OperationalKPIData.__table__.columns)
    if not include_device_data:
        columns = [
            (
                sa.literal(None).label(column.name)
                if column.name == "device_data_json"
                else column
            )
            for column in columns
        ]
    query = select(*columns)
    if project_ids:
        query = query.where(models.OperationalKPIData.project_id.in_(project_ids))
    if kpi_type_ids:
        query = query.where(models.OperationalKPIData.kpi_type_id.in_(kpi_type_ids))
    query = query.where(models.OperationalKPIData.date >= start)
    query = query.where(models.OperationalKPIData.date < end)

    return DbQuery(query=query)
