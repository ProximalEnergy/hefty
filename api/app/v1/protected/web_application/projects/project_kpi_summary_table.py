import datetime
from typing import Annotated

import numpy as np
import pandas as pd
from core.db_query import DbQuery, OutputType
from fastapi import APIRouter, Depends
from pandas.tseries.offsets import DateOffset
from pydantic import BaseModel
from sqlalchemy import case, select

from app import interfaces
from app._dependencies.filtering import get_company_project_data_access_start_time
from app.dependencies import (
    get_is_superadmin_async,
    get_project_api,
    get_user_data_async,
)
from core import models

router = APIRouter()


class TimeHorizonStart(BaseModel):
    """Model containing the start dates for different time horizon calculations.

    Includes start dates for week (7 days), month (30 days),
    year-to-date (YTD), and year (365 days) aggregations.
    """

    week: datetime.date
    month: datetime.date
    ytd: datetime.date
    year: datetime.date


class KPISummaryTableRow(BaseModel):
    """Model representing a single row in the KPI summary table.

    Contains KPI metadata, aggregated values for different time horizons
    (yesterday, week, month, ytd, year), threshold values for status calculation,
    and trend data for sparkline visualization.
    """

    kpi_type_id: int
    is_favorite: bool
    is_contract_kpi: bool
    is_hidden: bool
    device_type_id: int
    device_type_name_long: str
    name_long: str
    name_metric: str
    name_short: str
    description: str | None
    unit: str | None
    yesterday: float | None
    week: float | None
    month: float | None
    ytd: float | None
    year: float | None
    critical_low: float | None
    warning_low: float | None
    warning_high: float | None
    critical_high: float | None
    trend_data: list[
        float | None
    ]  # Always 365 elements, aligned with KPISummaryTable.trend_dates


class KPISummaryTable(BaseModel):
    """Response model for the KPI summary table endpoint.

    Contains the reference date (yesterday), start dates for time horizons,
    a common trend dates array (365 days), and the list of KPI rows with
    aggregated values and metadata.
    """

    yesterday: datetime.date
    start: TimeHorizonStart
    trend_dates: list[
        datetime.date
    ]  # Common 365-day array from year_start to yesterday
    rows: list[KPISummaryTableRow]


@router.get("/kpi-summary-table", response_model=KPISummaryTable)
async def get_project_kpi_summary_table(
    user_data: Annotated[interfaces.UserData, Depends(get_user_data_async)],
    is_superadmin: Annotated[bool, Depends(get_is_superadmin_async)],
    project: Annotated[models.Project, Depends(get_project_api)],
    data_access_start_time: Annotated[
        datetime.datetime, Depends(get_company_project_data_access_start_time)
    ],
):
    """API endpoint that returns aggregated KPI data for a project.

    Calculates KPI values for multiple time horizons (yesterday, week, month,
    ytd, year) and includes 365 days of trend data for sparkline visualization.
    Performs authorization checks and calculates date intervals based on the
    project's time zone.
    """
    # calculate date intervals
    yesterday: datetime.date = (
        pd.Timestamp.now(tz=project.time_zone).floor("D") - DateOffset(days=1)
    ).date()
    week_start = yesterday - datetime.timedelta(days=6)
    month_start = yesterday - datetime.timedelta(days=29)
    ytd_start = datetime.date(yesterday.year, 1, 1)
    year_start = yesterday - datetime.timedelta(days=364)

    data_access_start_date = data_access_start_time.date()
    if data_access_start_date > year_start:
        year_start = data_access_start_date

    # Generate common trend_dates array (365 days from year_start to yesterday)
    trend_dates = [year_start + datetime.timedelta(days=i) for i in range(365)]

    # Combined query: get KPI metadata and time-series data
    # First, create a subquery for contract KPIs for this project
    contract_kpi_subquery = (
        select(models.ContractKPI.kpi_type_id)
        .select_from(models.ContractKPI)
        .join(
            models.Contract,
            models.ContractKPI.contract_id == models.Contract.contract_id,
        )
        .where(models.Contract.project_id == project.project_id)
        .distinct()
    ).subquery()

    query = (
        select(
            # Metadata columns
            models.KPIType.kpi_type_id,
            models.KPIType.name_long,
            models.KPIType.name_metric,
            models.KPIType.name_short,
            models.KPIType.description,
            models.KPIType.unit,
            models.KPIType.aggregation_method,
            models.KPIType.critical_low,
            models.KPIType.warning_low,
            models.KPIType.warning_high,
            models.KPIType.critical_high,
            models.KPIType.device_type_id,
            models.DeviceType.name_long.label("device_type_name_long"),
            case(
                (contract_kpi_subquery.c.kpi_type_id.isnot(None), True),
                else_=False,
            ).label("is_contract_kpi"),
            # Favorite status
            case(
                (models.UserKPITypes.kpi_type_id.isnot(None), True),
                else_=False,
            ).label("is_favorite"),
            # Visibility status
            models.KPIInstance.is_visible.label("is_visible"),
            # Time-series columns
            models.OperationalKPIData.date,
            models.OperationalKPIData.project_data,
        )
        .select_from(models.OperationalKPIData)
        .join(
            models.KPIInstance,
            (models.OperationalKPIData.kpi_type_id == models.KPIInstance.kpi_type_id)
            & (models.OperationalKPIData.project_id == models.KPIInstance.project_id),
        )
        .join(
            models.KPIType,
            models.KPIInstance.kpi_type_id == models.KPIType.kpi_type_id,
        )
        .join(
            models.DeviceType,
            models.KPIType.device_type_id == models.DeviceType.device_type_id,
        )
        .outerjoin(
            contract_kpi_subquery,
            models.KPIType.kpi_type_id == contract_kpi_subquery.c.kpi_type_id,
        )
        .outerjoin(
            models.UserKPITypes,
            (models.KPIType.kpi_type_id == models.UserKPITypes.kpi_type_id)
            & (models.UserKPITypes.user_id == user_data.user_id)
            & (models.UserKPITypes.is_favorited == True),
        )
    )

    # Build WHERE clause conditions
    where_conditions = [
        models.OperationalKPIData.project_id == project.project_id,
        models.OperationalKPIData.date >= year_start,
        models.OperationalKPIData.date <= yesterday,
        models.OperationalKPIData.project_data.isnot(None),
    ]

    # Only filter by is_visible for non-superadmin users
    if not is_superadmin:
        where_conditions.append(models.KPIInstance.is_visible == True)

    query = query.where(*where_conditions)

    combined_df = await DbQuery(query=query).get_async(output_type=OutputType.PANDAS)

    # Filter out None and inf values from project_data
    if not combined_df.empty:
        combined_df = combined_df[
            (combined_df["project_data"].notna())
            & (np.isfinite(combined_df["project_data"]))
        ]

    # Process the combined dataframe
    rows: list[KPISummaryTableRow] = []

    if combined_df.empty:
        return KPISummaryTable(
            yesterday=yesterday,
            start=TimeHorizonStart(
                week=week_start,
                month=month_start,
                ytd=ytd_start,
                year=year_start,
            ),
            trend_dates=trend_dates,
            rows=[],
        )

    # Group by kpi_type_id to process each KPI separately
    for kpi_type_id, group_df in combined_df.groupby("kpi_type_id"):
        # Convert kpi_type_id to int (from pandas groupby)
        kpi_type_id_int = int(kpi_type_id)  # type: ignore[arg-type]
        # Get metadata (same for all rows in group)
        first_row = group_df.iloc[0]
        name_long = first_row["name_long"]
        name_metric = first_row["name_metric"]
        name_short = first_row["name_short"]
        description = (
            first_row["description"] if pd.notna(first_row["description"]) else None
        )
        unit = first_row["unit"] if pd.notna(first_row["unit"]) else None
        aggregation_method = first_row["aggregation_method"]
        device_type_id = int(first_row["device_type_id"])
        device_type_name_long = str(first_row["device_type_name_long"])
        is_contract_kpi = bool(first_row["is_contract_kpi"])
        is_favorite = bool(first_row.get("is_favorite", False))
        is_visible = bool(first_row.get("is_visible", True))
        is_hidden = not is_visible
        critical_low = (
            float(first_row["critical_low"])
            if pd.notna(first_row["critical_low"])
            else None
        )
        warning_low = (
            float(first_row["warning_low"])
            if pd.notna(first_row["warning_low"])
            else None
        )
        warning_high = (
            float(first_row["warning_high"])
            if pd.notna(first_row["warning_high"])
            else None
        )
        critical_high = (
            float(first_row["critical_high"])
            if pd.notna(first_row["critical_high"])
            else None
        )

        # Get time-series data for this KPI
        data_df = group_df[["date", "project_data"]].copy()
        data_df = data_df.sort_values("date")

        # Calculate aggregated values
        # Yesterday value
        yesterday_data = data_df[data_df["date"] == yesterday]
        yesterday_value = None
        if not yesterday_data.empty and pd.notna(
            yesterday_data["project_data"].iloc[0]
        ):
            value = float(yesterday_data["project_data"].iloc[0])
            # Convert inf/-inf to None
            yesterday_value = None if np.isinf(value) else value

        # Helper function to aggregate based on aggregation_method
        def aggregate_values(*, df: pd.DataFrame) -> float | None:
            """Aggregate values based on the aggregation method.

            Args:
                df: The dataframe to aggregate.
            """
            if df.empty or df["project_data"].isna().all():
                return None
            values = df["project_data"].dropna()
            if values.empty:
                return None

            # Filter out inf/-inf values
            values = values[np.isfinite(values)]
            if values.empty:
                return None

            if aggregation_method == "sum":
                return float(values.sum())
            elif aggregation_method == "average":
                return float(values.mean())
            elif aggregation_method == "min":
                return float(values.min())
            elif aggregation_method == "max":
                return float(values.max())
            else:
                # Default to average if unknown method
                return float(values.mean())

        # Week aggregation
        week_data = data_df[
            (data_df["date"] >= week_start) & (data_df["date"] <= yesterday)
        ]
        week_value = aggregate_values(df=week_data)

        # Month aggregation
        month_data = data_df[
            (data_df["date"] >= month_start) & (data_df["date"] <= yesterday)
        ]
        month_value = aggregate_values(df=month_data)

        # YTD aggregation
        ytd_data = data_df[
            (data_df["date"] >= ytd_start) & (data_df["date"] <= yesterday)
        ]
        ytd_value = aggregate_values(df=ytd_data)

        # Year aggregation
        year_data = data_df[
            (data_df["date"] >= year_start) & (data_df["date"] <= yesterday)
        ]
        year_value = aggregate_values(df=year_data)

        # Build trend_data array aligned with common trend_dates (365 elements)
        # Create a map from date to value for O(1) lookup
        data_map: dict[datetime.date, float | None] = {}
        for _, data_row in data_df.iterrows():
            date_val = data_row["date"]
            value = data_row["project_data"]

            # Convert date to datetime.date object
            if isinstance(date_val, pd.Timestamp):
                date_obj = date_val.date()
            elif isinstance(date_val, datetime.date):
                date_obj = date_val
            else:
                # Fallback: try to parse string or use today
                date_obj = datetime.date.today()

            # Convert value, handling NaN/None and inf values
            if pd.isna(value):
                value_float = None
            else:
                value_float = float(value)
                # Convert inf/-inf to None
                if np.isinf(value_float):
                    value_float = None

            data_map[date_obj] = value_float

        # Build trend_data array with 365 elements, aligned with common trend_dates
        trend_data = []
        for date in trend_dates:
            trend_data.append(data_map.get(date, None))

        # Build KPISummaryTableRow
        row = KPISummaryTableRow(
            kpi_type_id=kpi_type_id_int,
            is_favorite=is_favorite,
            is_contract_kpi=is_contract_kpi,
            is_hidden=is_hidden,
            device_type_id=device_type_id,
            device_type_name_long=device_type_name_long,
            name_long=name_long,
            name_metric=name_metric,
            name_short=name_short,
            description=description,
            unit=unit,
            yesterday=yesterday_value,
            week=week_value,
            month=month_value,
            ytd=ytd_value,
            year=year_value,
            critical_low=critical_low,
            warning_low=warning_low,
            warning_high=warning_high,
            critical_high=critical_high,
            trend_data=trend_data,
        )
        rows.append(row)

    # Sort rows by favorites first, then by name_long
    rows.sort(key=lambda x: (not x.is_favorite, x.is_hidden, x.name_long))

    return KPISummaryTable(
        yesterday=yesterday,
        start=TimeHorizonStart(
            week=week_start,
            month=month_start,
            ytd=ytd_start,
            year=year_start,
        ),
        trend_dates=trend_dates,
        rows=rows,
    )
