import datetime
import logging
from enum import StrEnum
from typing import Annotated, Any, cast
from uuid import UUID
from zoneinfo import ZoneInfo

import core.models as models
import pandas as pd
from core.crud.operational.calendar import (
    get_calendar_item_assignments,
    get_calendar_item_exceptions,
    get_calendar_items,
)
from core.crud.operational.kpi_data import core_get_kpi_data
from core.crud.operational.projects import get_projects
from core.db_query import OutputType, postprocess_pandas_df
from core.enumerations import KPITypeEnum, ProjectTypeEnum, SensorTypeEnum
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces, utils
from app._crud.operational import calendar as crud_calendar
from app._crud.operational.data_timeseries import get_operational_data_timeseries
from app._crud.operational.portfolio_bess_power_availability import (
    get_portfolio_bess_power_availability_metrics,
)
from app._dependencies.authentication import get_user
from app.integrations.providers import ptp_explorer
from app.integrations.token_manager import TokenManager
from app.interfaces import CalendarItemInterface, UserAuthed

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"],
    include_in_schema=utils.get_include_in_schema(),
)


class PortfolioHomeShortTerm(BaseModel):
    """todo"""

    project_id: UUID
    power: float | None
    poa: float | None
    soc: float | None
    times: list[Any] | None
    meter_active_power: list[Any] | None
    meter_soc_percent: list[Any] | None
    max_charge_power: list[Any] | None
    max_discharge_power: list[Any] | None
    expected_power: list[Any] | None
    performance_index: float | None


class PortfolioHomeLongTerm(BaseModel):
    """Long-term portfolio home metrics."""

    project_id: UUID
    times: list[Any] | None
    cycle_count_string: list[Any] | None
    state_of_health: list[Any] | None
    pcs_mechanical_availability: list[Any] | None
    energy_production: list[Any] | None


class PortfolioHome(PortfolioHomeShortTerm, PortfolioHomeLongTerm):
    """Combined short- and long-term portfolio home metrics."""


def _calendar_value_or_none(*, value: Any) -> Any:
    """Normalize pandas scalar nulls while preserving list-like values.

    Args:
        value: Scalar or list-like value to normalize.
    """
    if isinstance(value, list | tuple):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return value
    return value


def _append_calendar_exception(
    *,
    exdates_by_item: dict[Any, list[str]],
    calendar_item_id: Any,
    exception_date: Any,
) -> None:
    """Append a cancelled exception date to the item map.

    Args:
        exdates_by_item: Mapping of calendar item id to list of exception dates.
        calendar_item_id: Key identifying the calendar item.
        exception_date: Date value to append; no-op if NaT/NaN.
    """
    if pd.isna(exception_date):
        return
    exdate = (
        exception_date.isoformat()
        if hasattr(exception_date, "isoformat")
        else str(exception_date)
    )
    exdates_by_item.setdefault(calendar_item_id, []).append(exdate)


def _append_calendar_assignment(
    *,
    assignees_by_item: dict[Any, dict[str, list[Any]]],
    calendar_item_id: Any,
    user_id: Any,
    team_id: Any,
) -> None:
    """Append an assignment id to the item map.

    Args:
        assignees_by_item: Mapping of calendar item id to assignee id lists.
        calendar_item_id: Key identifying the calendar item.
        user_id: User assignee id to append; skipped if NaN.
        team_id: Team assignee id to append; skipped if NaN.
    """
    assignees = assignees_by_item.setdefault(
        calendar_item_id,
        {"assignee_user_ids": [], "assignee_team_ids": []},
    )
    if pd.notna(user_id):
        assignees["assignee_user_ids"].append(user_id)
    if pd.notna(team_id):
        assignees["assignee_team_ids"].append(team_id)


class PortfolioBessPowerAvailability(BaseModel):
    """Latest BESS PCS power availability using POI and PCS denominators."""

    project_id: UUID
    available_power_mw: float | None
    poi_capacity_mw: float | None
    max_pcs_capacity_mw: float | None
    num_pcs_units: int | None
    power_availability_pct_poi: float | None
    power_availability_pct_pcs: float | None


class PortfolioMarketPerformanceHasAccessRequest(BaseModel):
    """Project IDs to check for QSE market-performance access."""

    project_ids: list[UUID] = Field(
        default_factory=list,
        description="Operational project UUIDs (intersected with caller access).",
    )


class PortfolioMarketPerformanceHasAccessRow(BaseModel):
    """QSE integration + company permission flag for one project."""

    project_id: UUID
    has_access: bool


class PortfolioBessRevenueSummaryRequest(BaseModel):
    """Project IDs to batch-fetch QSE settlement revenue for."""

    project_ids: list[UUID] = Field(
        default_factory=list,
        description="Operational project UUIDs (intersected with caller access).",
    )


class PortfolioBessRevenueSummaryRow(BaseModel):
    """QSE settlement revenue totals for one BESS project."""

    project_id: UUID
    revenue_today: float | None
    revenue_mtd: float | None
    revenue_ytd: float | None


_NEGATE_KEYS = frozenset({"DAEPAMT", "DAESAMT", "RTEIAMT"})


def _should_negate_settlement_key(*, key_name: str) -> bool:
    """Return True if this settlement key represents a cost (should be negated).

    Args:
        key_name: PTP data-point key name.
    """
    k = key_name.upper()
    return k in _NEGATE_KEYS or "SPD" in k or "BPD" in k


def _parse_settlement_number(*, value: Any) -> float:
    """Parse a PTP data value to float, returning 0.0 on failure.

    Args:
        value: Raw value from PTP API response.
    """
    if value is None:
        return 0.0
    try:
        n = float(value)
        return n if not (n != n) else 0.0  # guard NaN
    except (TypeError, ValueError):
        return 0.0


def _aggregate_settlement_element(
    *,
    element: dict[str, Any],
    tz_str: str,
    now_utc: datetime.datetime,
) -> tuple[float, float, float]:
    """Accumulate today/MTD/YTD revenue from one PTP Settlement-Charges element.

    Replicates the aggregation logic from the frontend useBESSRevenueSummary hook:
    picks the highest-sequence data entry per interval, negates cost keys, and
    buckets into today / month-to-date / year-to-date using the project timezone.

    Args:
        element: Single element dict from PTP API ``data`` array.
        tz_str: IANA timezone string for the project.
        now_utc: Current UTC datetime (shared across projects for consistency).

    Returns:
        Tuple of (revenue_today, revenue_mtd, revenue_ytd) in USD.
    """
    try:
        tz = ZoneInfo(tz_str)
        now_local = now_utc.astimezone(tz)
    except Exception:
        now_local = now_utc

    today_key = now_local.strftime("%Y-%m-%d")
    month_start_key = now_local.replace(day=1).strftime("%Y-%m-%d")

    today = 0.0
    mtd = 0.0
    ytd = 0.0

    for dp in element.get("dataPoints", []):
        if not isinstance(dp, dict):
            continue
        sign = (
            -1 if _should_negate_settlement_key(key_name=dp.get("keyName", "")) else 1
        )
        for val in dp.get("values", []):
            if not isinstance(val, dict):
                continue
            interval = val.get("intervalStartUtc")
            if not interval:
                continue
            data_entries = val.get("data") or []
            if not data_entries:
                continue
            best = max(
                data_entries,
                key=lambda e: (
                    e.get("sequence", 0)
                    if isinstance(e.get("sequence"), (int, float))
                    else 0
                ),
            )
            n = _parse_settlement_number(value=best.get("value")) * sign
            try:
                dt_utc = datetime.datetime.fromisoformat(
                    interval.replace("Z", "+00:00")
                )
                dt_local = dt_utc.astimezone(ZoneInfo(tz_str))
                date_key = dt_local.strftime("%Y-%m-%d")
            except Exception:
                continue
            ytd += n
            if date_key >= month_start_key:
                mtd += n
            if date_key == today_key:
                today += n

    return today, mtd, ytd


class TimeFrame(StrEnum):
    """Time window options for portfolio metrics."""

    H24 = "24h"
    D30 = "30d"


async def get_portfolio_home_short_term(
    *,
    project_ids: list[UUID],
    db: AsyncSession,
) -> list[PortfolioHomeShortTerm]:
    """Fetch short-term portfolio home metrics for projects.

    Args:
        project_ids: Project identifiers to include.
        db: Async database session.
    """
    if len(project_ids) == 0:
        return []

    projects_query = get_projects(project_ids=project_ids)
    projects_df = await projects_query.get_async(output_type=OutputType.PANDAS)
    projects_df = postprocess_pandas_df(df=projects_df, index="project_id")

    real_time_project_ids = projects_df[
        projects_df["has_real_time_data"]
    ].index.tolist()
    day_behind_project_ids = projects_df[
        ~projects_df["has_real_time_data"]
    ].index.tolist()

    # end equal to current time in utc
    end = pd.Timestamp.now("UTC").floor("5min")

    # start equal to end minus 1 day
    start = end - pd.Timedelta(days=1)
    df = pd.DataFrame()
    df_day_behind = pd.DataFrame()

    # Query data
    if real_time_project_ids:
        data_timeseries = await get_operational_data_timeseries(
            db,
            start=start,
            end=end,
            project_ids=real_time_project_ids,
        )

        # Parse data into a DataFrame
        df = pd.DataFrame.from_records([d.__dict__ for d in data_timeseries])

        if not df.empty:
            # Collapse value columns into a single column
            df["value"] = df.filter(regex="value_").bfill(axis=1).iloc[:, 0]
            df = df.infer_objects()

            # Select the relevant columns
            df = df[["time", "project_id", "tag_id", "sensor_type_id", "value"]]

    if day_behind_project_ids:
        day_behind_start = (
            start.tz_convert(
                projects_df.loc[day_behind_project_ids, "time_zone"].values[0]
            )
            .normalize()
            .tz_convert("UTC")
        )
        day_behind_end = day_behind_start + pd.Timedelta(days=1)

        data_timeseries_day_behind = await get_operational_data_timeseries(
            db,
            start=day_behind_start,
            end=day_behind_end,
            project_ids=day_behind_project_ids,
        )

        # Parse data into a DataFrame
        df_day_behind = pd.DataFrame.from_records(
            [d.__dict__ for d in data_timeseries_day_behind]
        )

        if not df_day_behind.empty:
            # Collapse value columns into a single column
            df_day_behind["value"] = (
                df_day_behind.filter(regex="value_").bfill(axis=1).iloc[:, 0]
            )
            df_day_behind = df_day_behind.infer_objects()

            # Select the relevant columns
            df_day_behind = df_day_behind[
                ["time", "project_id", "tag_id", "sensor_type_id", "value"]
            ]

    if day_behind_project_ids and real_time_project_ids:
        # Create a full date range to be used for each project DataFrame
        date_range = pd.date_range(
            start=day_behind_start, end=end, freq="5min", inclusive="left"
        )
    elif day_behind_project_ids:
        date_range = pd.date_range(
            start=day_behind_start, end=day_behind_end, freq="5min", inclusive="left"
        )
    elif real_time_project_ids:
        date_range = pd.date_range(start=start, end=end, freq="5min", inclusive="left")

    return_data = []
    df = pd.concat([df, df_day_behind])

    for project_id in project_ids:
        if not df.empty:
            df_project = df[df["project_id"] == project_id]
        else:
            df_project = pd.DataFrame()

        if df_project.empty:
            return_data.append(
                PortfolioHomeShortTerm(
                    project_id=project_id,
                    power=None,
                    poa=None,
                    soc=None,
                    times=None,
                    meter_active_power=None,
                    meter_soc_percent=None,
                    max_charge_power=None,
                    max_discharge_power=None,
                    expected_power=None,
                    performance_index=None,
                ),
            )
        else:
            # Pivot the DataFrame to have a multi-level column index
            df_project = df_project.pivot(
                index="time",
                columns=["tag_id", "sensor_type_id"],
                values="value",
            )

            # Reindex the DataFrame to include all timestamps
            df_project = df_project.reindex(date_range)

            # Sort the DataFrame by index
            df_project = df_project.sort_index()

            # Forward fill the missing values
            df_project = df_project.ffill()

            times = df_project.index.tolist()

            power_columns = [
                c for c in df_project.columns if c[1] == 1
            ]  # meter_active_power
            meter_active_power = df_project[power_columns].mean(axis=1).tolist()
            power = meter_active_power[-1]

            # POA columns
            poa_columns = [
                c for c in df_project.columns if c[1] == 4
            ]  # met_station_poa
            poa = df_project[poa_columns].mean(axis=1).tolist()[-1]

            # SOC Columns
            soc_columns = [
                c for c in df_project.columns if c[1] == 32
            ]  # project_soc_percent
            if soc_columns:
                meter_soc_percent = df_project[soc_columns].mean(axis=1).tolist()
                soc = meter_soc_percent[-1]
                if isinstance(soc, float):
                    soc *= 100
            else:
                meter_soc_percent = None
                soc = None

            max_charge_columns = [
                c for c in df_project.columns if c[1] == 80
            ]  # max_charge_power
            if max_charge_columns:
                poi_value = projects_df.loc[project_id]["poi"]  # type: ignore
                poi = pd.to_numeric(poi_value, errors="coerce")
                max_charge_power = (
                    (-df_project[max_charge_columns].sum(axis=1))
                    .clip(lower=-poi)
                    .tolist()
                )
            else:
                max_charge_power = None
            max_discharge_columns = [
                c for c in df_project.columns if c[1] == 81
            ]  # max_discharge_power
            if max_discharge_columns:
                poi_value = projects_df.loc[project_id]["poi"]  # type: ignore
                poi = pd.to_numeric(poi_value, errors="coerce")
                max_discharge_power = (
                    df_project[max_discharge_columns]
                    .sum(axis=1)
                    .clip(upper=poi)
                    .tolist()
                )
            else:
                max_discharge_power = None

            expected_columns = [
                c for c in df_project.columns if c[0] == -1
            ]  # -1 will always be the expected power tag_id
            if expected_columns != []:
                expected_power = df_project[expected_columns].mean(axis=1).tolist()
            else:
                expected_power = None

            if power_columns and expected_columns:
                time_zone: str = projects_df.loc[project_id, "time_zone"]  # type: ignore
                project_type_id = projects_df.loc[project_id, "project_type_id"]  # type: ignore
                if project_type_id == ProjectTypeEnum.PVS:  # PV + Storage
                    circuit_power_columns = [
                        c
                        for c in df_project.columns
                        if c[1]
                        == SensorTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER  # noqa: E501
                    ]  # pv_mv_circuit_meter_active_power
                    meter_total = (
                        df_project.loc[
                            pd.Timestamp.now().tz_localize(time_zone).floor("D") :,
                            circuit_power_columns,
                        ]
                        .clip(lower=0)
                        .sum(axis=1)
                        .sum()
                    )
                else:
                    meter_total = (
                        df_project.loc[
                            pd.Timestamp.now().tz_localize(time_zone).floor("D") :,
                            power_columns,
                        ]
                        .clip(lower=0)
                        .sum(axis=1)
                        .sum()
                    )
                expected_total = (
                    df_project.loc[
                        pd.Timestamp.now().tz_localize(time_zone).floor("D") :,
                        expected_columns,
                    ]
                    .clip(lower=0)
                    .sum(axis=1)
                    .sum()
                )
                if expected_total > 0:
                    performance_index = meter_total / expected_total * 100
                else:
                    performance_index = None
            else:
                performance_index = None

            return_data.append(
                PortfolioHomeShortTerm(
                    project_id=project_id,
                    power=power,
                    poa=poa,
                    soc=soc,
                    times=times,
                    meter_active_power=meter_active_power,
                    meter_soc_percent=meter_soc_percent,
                    max_charge_power=max_charge_power,
                    max_discharge_power=max_discharge_power,
                    expected_power=expected_power,
                    performance_index=performance_index,
                ),
            )

    return return_data


async def get_portfolio_home_long_term(
    *,
    project_ids: list[UUID],
    db: AsyncSession,
) -> list[PortfolioHomeLongTerm]:
    """Fetch long-term portfolio home metrics for projects.

    Args:
        project_ids: Project identifiers to include.
        db: Async database session.
    """
    if len(project_ids) == 0:
        return []

    # KPI type IDs for long-term data
    kpi_type_ids = [
        KPITypeEnum.BESS_STRING_CYCLE_COUNT.value,
        KPITypeEnum.BESS_STRING_SOH.value,
        KPITypeEnum.PV_INVERTER_MECHANICAL_AVAILABILITY.value,
        KPITypeEnum.PROJECT_ENERGY_PRODUCTION.value,
    ]

    # end equal to current date in UTC
    end_date = pd.Timestamp.now("UTC").floor("D").date()

    # start equal to end minus 30 days
    start_date = (pd.Timestamp.now("UTC").floor("D") - pd.Timedelta(days=30)).date()

    # Query KPI data
    kpi_df = await core_get_kpi_data(
        start=start_date,
        end=end_date,
        project_ids=project_ids,
        kpi_type_ids=kpi_type_ids,
        include_device_data=False,
    ).get_async(
        executor=db,
        output_type=OutputType.PANDAS,
    )

    if kpi_df.empty:
        return [
            PortfolioHomeLongTerm(
                project_id=project_id,
                times=None,
                cycle_count_string=None,
                state_of_health=None,
                pcs_mechanical_availability=None,
                energy_production=None,
            )
            for project_id in project_ids
        ]

    # Create date range for 30 days
    date_range = pd.date_range(
        start=start_date, end=end_date, freq="D", inclusive="left"
    )

    return_data = []

    for project_id in project_ids:
        df_project = kpi_df[kpi_df["project_id"] == project_id]

        if df_project.empty:
            return_data.append(
                PortfolioHomeLongTerm(
                    project_id=project_id,
                    times=None,
                    cycle_count_string=None,
                    state_of_health=None,
                    pcs_mechanical_availability=None,
                    energy_production=None,
                ),
            )
        else:
            # Pivot the DataFrame to have kpi_type_id as columns
            df_pivot = df_project.pivot(
                index="date",
                columns="kpi_type_id",
                values="project_data",
            )

            # Reindex to include all dates in the range
            df_pivot = df_pivot.reindex(date_range)

            # Sort by date
            df_pivot = df_pivot.sort_index()

            # Convert dates to list
            times = df_pivot.index.tolist()

            # Extract values for each KPI type
            cycle_count_string = (
                df_pivot[32].tolist() if 32 in df_pivot.columns else None
            )
            state_of_health = df_pivot[54].tolist() if 54 in df_pivot.columns else None
            pcs_mechanical_availability = (
                df_pivot[int(KPITypeEnum.PV_INVERTER_MECHANICAL_AVAILABILITY)].tolist()
                if int(KPITypeEnum.PV_INVERTER_MECHANICAL_AVAILABILITY)
                in df_pivot.columns
                else None
            )
            energy_production = (
                df_pivot[int(KPITypeEnum.PROJECT_ENERGY_PRODUCTION)].tolist()
                if int(KPITypeEnum.PROJECT_ENERGY_PRODUCTION) in df_pivot.columns
                else None
            )

            return_data.append(
                PortfolioHomeLongTerm(
                    project_id=project_id,
                    times=times,
                    cycle_count_string=cycle_count_string,
                    state_of_health=state_of_health,
                    pcs_mechanical_availability=pcs_mechanical_availability,
                    energy_production=energy_production,
                ),
            )

    return return_data


@router.get(
    "/bess-power-availability",
    response_model=list[PortfolioBessPowerAvailability],
    operation_id="get_portfolio_bess_power_availability",
)
async def get_portfolio_bess_power_availability_route(
    project_ids: Annotated[list[UUID] | None, Query()] = None,
    db: AsyncSession = Depends(dependencies.get_async_db),
    user_data: UserAuthed = Depends(get_user),
):
    """Return latest PCS power availability for many projects in one query.

    Reads DISTINCT ON latest rows from operational.data_timeseries for PCS
    available charge/discharge power tags.

    Args:
        project_ids: Optional filter; defaults to all projects the user may
            access when omitted.
        db: Async operational database session.
        user_data: Authenticated user for access control.
    """
    if not project_ids:
        allowed = list(user_data.operational_project_ids)
    else:
        allowed = list(set(project_ids) & set(user_data.operational_project_ids))

    if not allowed:
        return []

    projects_query = get_projects(project_ids=allowed)
    projects_df = await projects_query.get_async(output_type=OutputType.PANDAS)

    poi_by_project: dict[UUID, float | None] = {pid: None for pid in allowed}
    schema_by_project: dict[UUID, str] = {}
    if not projects_df.empty:
        projects_df = postprocess_pandas_df(df=projects_df, index="project_id")
        valid_pids = projects_df.index.intersection(allowed)
        if not valid_pids.empty:
            projects_df["poi"] = pd.to_numeric(projects_df["poi"], errors="coerce")
            sub = projects_df.reindex(list(valid_pids))
            poi_raw = cast(dict[UUID, Any], sub["poi"].to_dict())
            poi_updates = {
                pid: (None if pd.isna(val) else float(val))
                for pid, val in poi_raw.items()
            }
            poi_by_project.update(poi_updates)
            schema_updates = sub["name_short"].dropna().to_dict()
            schema_by_project.update(cast(dict[UUID, str], schema_updates))

    metrics_map = await get_portfolio_bess_power_availability_metrics(
        db=db,
        project_ids=allowed,
        poi_by_project=poi_by_project,
        project_schema_by_id=schema_by_project,
    )

    return [
        PortfolioBessPowerAvailability(
            project_id=pid,
            available_power_mw=metrics_map[pid].available_power_mw,
            poi_capacity_mw=metrics_map[pid].poi_capacity_mw,
            max_pcs_capacity_mw=metrics_map[pid].max_pcs_capacity_mw,
            num_pcs_units=metrics_map[pid].num_pcs_units,
            power_availability_pct_poi=metrics_map[pid].power_availability_pct_poi,
            power_availability_pct_pcs=metrics_map[pid].power_availability_pct_pcs,
        )
        for pid in allowed
    ]


@router.post(
    "/market-performance/has-access",
    operation_id="post_portfolio_market_performance_has_access",
)
async def post_portfolio_market_performance_has_access(
    body: PortfolioMarketPerformanceHasAccessRequest,
    db: AsyncSession = Depends(dependencies.get_async_db),
    user_data: UserAuthed = Depends(get_user),
) -> list[PortfolioMarketPerformanceHasAccessRow]:
    """Return QSE market access for many projects in one request.

    Same rules as GET
    ``/projects/{project_id}/market-performance/has-access`` for each id:
    project has a QSE integration and the user's company has can_view on it.

    Args:
        body: Project IDs to check; non-accessible ids are ignored.
        db: Async operational database session.
        user_data: Authenticated user for access filtering and company_id.

    Returns:
        One entry per requested project the user may access, with has_access.
    """
    allowed = list(set(body.project_ids) & set(user_data.operational_project_ids))
    if not allowed:
        return []

    stmt = (
        select(models.QSEIntegration.project_id)
        .join(
            models.QSEPermission,
            models.QSEPermission.qse_integration_id
            == models.QSEIntegration.qse_integration_id,
        )
        .where(
            models.QSEIntegration.project_id.in_(allowed),
            models.QSEPermission.company_id == user_data.company_id,
            models.QSEPermission.can_view.is_(True),
        )
        .distinct()
    )
    result = await db.execute(stmt)
    with_access = set(result.scalars().all())

    allowed_sorted = sorted(allowed, key=lambda u: str(u))
    return [
        PortfolioMarketPerformanceHasAccessRow(
            project_id=pid,
            has_access=pid in with_access,
        )
        for pid in allowed_sorted
    ]


@router.post(
    "/bess-revenue-summary",
    operation_id="post_portfolio_bess_revenue_summary",
)
async def post_portfolio_bess_revenue_summary(
    body: PortfolioBessRevenueSummaryRequest,
    db: AsyncSession = Depends(dependencies.get_async_db),
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
    user_data: UserAuthed = Depends(get_user),
) -> list[PortfolioBessRevenueSummaryRow]:
    """Batch fetch QSE settlement revenue for multiple BESS projects.

    Fetches Settlement-Charges from the PTP API for all allowed projects in a
    single API call rather than one request per project, eliminating the N+1
    pattern that occurs when using the per-project ptp-data endpoint.

    Args:
        body: Project IDs to fetch; non-accessible IDs are ignored.
        db: Async operational database session.
        tps_token: PTP API token manager.
        user_data: Authenticated user for access control.
    """
    allowed = list(set(body.project_ids) & set(user_data.operational_project_ids))
    if not allowed:
        return []

    integrations_result = await db.execute(
        select(models.QSEIntegration).where(
            models.QSEIntegration.project_id.in_(allowed)
        )
    )
    perms_result = await db.execute(
        select(models.QSEPermission).where(
            models.QSEPermission.company_id == user_data.company_id,
            models.QSEPermission.can_view.is_(True),
        )
    )
    integrations = list(integrations_result.scalars().all())
    allowed_qse_ids = {p.qse_integration_id for p in perms_result.scalars().all()}

    project_to_identifier: dict[UUID, str] = {}
    for integration in integrations:
        if integration.qse_integration_id not in allowed_qse_ids:
            continue
        if integration.qse_project_identifier:
            project_to_identifier[integration.project_id] = (
                integration.qse_project_identifier
            )

    if not project_to_identifier:
        return []

    projects_query = get_projects(project_ids=list(project_to_identifier.keys()))
    projects_df = await projects_query.get_async(output_type=OutputType.PANDAS)
    projects_df = postprocess_pandas_df(df=projects_df, index="project_id")
    tz_map = cast(dict[UUID, Any], projects_df["time_zone"].to_dict())
    tz_by_project: dict[UUID, str] = {
        pid: (
            str(raw)
            if (raw := tz_map.get(pid)) is not None and pd.notna(raw)
            else "UTC"
        )
        for pid in project_to_identifier
    }

    now_utc = datetime.datetime.now(datetime.UTC)
    begin_str = (
        datetime.datetime(now_utc.year - 1, 12, 31, tzinfo=datetime.UTC)
        .isoformat()
        .replace("+00:00", "Z")
    )
    end_str = (now_utc + datetime.timedelta(days=2)).isoformat().replace("+00:00", "Z")

    token = await tps_token.get_token()
    all_identifiers = list(set(project_to_identifier.values()))

    try:
        ptp_result = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint="Settlement-Charges",
            elements=all_identifiers,
            begin=begin_str,
            end=end_str,
        )
    except Exception:
        logger.exception("Failed to fetch PTP settlement data for portfolio")
        return []

    element_by_id: dict[str, dict[str, Any]] = {
        e["identifier"]: e
        for e in ptp_result.get("data", [])
        if isinstance(e, dict) and e.get("identifier")
    }

    result: list[PortfolioBessRevenueSummaryRow] = []
    for pid, identifier in project_to_identifier.items():
        element = element_by_id.get(identifier)
        if element is None:
            result.append(
                PortfolioBessRevenueSummaryRow(
                    project_id=pid,
                    revenue_today=None,
                    revenue_mtd=None,
                    revenue_ytd=None,
                )
            )
            continue

        today, mtd, ytd = _aggregate_settlement_element(
            element=element,
            tz_str=tz_by_project.get(pid, "UTC"),
            now_utc=now_utc,
        )
        result.append(
            PortfolioBessRevenueSummaryRow(
                project_id=pid,
                revenue_today=today,
                revenue_mtd=mtd,
                revenue_ytd=ytd,
            )
        )

    return result


@router.get(
    "/home",
    response_model=list[PortfolioHome],
)
async def get_home(
    project_ids: Annotated[list[UUID] | None, Query()] = None,
    db: AsyncSession = Depends(dependencies.get_async_db),
    user_data: UserAuthed = Depends(get_user),
    time: TimeFrame = Query(default=TimeFrame.H24),  # new parameter
):
    # If project_ids is not provided, default to all projects the user has access to
    """Return portfolio home metrics for the selected time frame.

    Args:
        project_ids: Optional project IDs to scope the response.
        db: Async database session.
        user_data: Authenticated user context used for access filtering.
        time: Time frame used to select short- or long-term data.
    """
    if project_ids is None:
        project_ids = user_data.operational_project_ids
    # If project_ids is provided, ensure they are within the user's access list
    else:
        project_ids = list(set(project_ids) & set(user_data.operational_project_ids))

    if time.value == TimeFrame.H24.value:
        short_term_data = await get_portfolio_home_short_term(
            project_ids=project_ids,
            db=db,
        )
        # Convert short-term data to PortfolioHome format
        return_data = [
            PortfolioHome(
                project_id=item.project_id,
                power=item.power,
                poa=item.poa,
                soc=item.soc,
                times=item.times,
                meter_active_power=item.meter_active_power,
                meter_soc_percent=item.meter_soc_percent,
                max_charge_power=item.max_charge_power,
                max_discharge_power=item.max_discharge_power,
                performance_index=item.performance_index,
                # Long-term fields set to None
                cycle_count_string=None,
                state_of_health=None,
                pcs_mechanical_availability=None,
                energy_production=None,
                expected_power=item.expected_power,
            )
            for item in short_term_data
        ]
    else:
        long_term_data = await get_portfolio_home_long_term(
            project_ids=project_ids,
            db=db,
        )
        # Convert long-term data to PortfolioHome format
        return_data = [
            PortfolioHome(
                project_id=item.project_id,
                # Short-term fields set to None
                power=None,
                poa=None,
                soc=None,
                expected_power=None,
                times=item.times,
                meter_active_power=None,
                meter_soc_percent=None,
                max_charge_power=None,
                max_discharge_power=None,
                performance_index=None,
                # Long-term fields
                cycle_count_string=item.cycle_count_string,
                state_of_health=item.state_of_health,
                pcs_mechanical_availability=item.pcs_mechanical_availability,
                energy_production=item.energy_production,
            )
            for item in long_term_data
        ]

    return return_data


@router.get(
    "/calendar",
    response_model=list[CalendarItemInterface],
)
async def get_portfolio_calendar_events(
    project_ids: Annotated[list[UUID] | None, Query()] = None,
    user_data: UserAuthed = Depends(get_user),
):
    """Get all calendar events for all projects in the user's portfolio.

    Args:
        project_ids: Optional project IDs to filter the results.
        user_data: Authenticated user context used for access filtering.
    """
    # If no project_ids provided, use all accessible projects
    if not project_ids:
        accessible_project_ids = user_data.operational_project_ids
    else:
        # Filter for projects the user can actually access
        accessible_project_ids = list(
            set(project_ids) & set(user_data.operational_project_ids)
        )

    if not accessible_project_ids:
        return []

    calendar_items_query = get_calendar_items(
        project_ids=accessible_project_ids,
        include_related=False,
    )
    calendar_items_df = await calendar_items_query.get_async(
        output_type=OutputType.PANDAS
    )

    if calendar_items_df.empty:
        return []

    calendar_item_ids = list(calendar_items_df["calendar_item_id"])

    exceptions_query = get_calendar_item_exceptions(calendar_item_ids=calendar_item_ids)
    exceptions_df = await exceptions_query.get_async(output_type=OutputType.PANDAS)
    exdates_by_item: dict[Any, list[str]] = {}
    for exception in exceptions_df.itertuples(index=False):
        if not exception.is_cancelled:
            continue
        _append_calendar_exception(
            exdates_by_item=exdates_by_item,
            calendar_item_id=exception.calendar_item_id,
            exception_date=exception.exception_date,
        )

    assignments_query = get_calendar_item_assignments(
        calendar_item_ids=calendar_item_ids
    )
    assignments_df = await assignments_query.get_async(output_type=OutputType.PANDAS)
    assignees_by_item: dict[Any, dict[str, list[Any]]] = {}
    for assignment in assignments_df.itertuples(index=False):
        _append_calendar_assignment(
            assignees_by_item=assignees_by_item,
            calendar_item_id=assignment.calendar_item_id,
            user_id=assignment.user_id,
            team_id=assignment.team_id,
        )

    # Shape the data into the final response model
    result_items = []
    for item in calendar_items_df.to_dict(orient="records"):
        calendar_item_id = item["calendar_item_id"]
        assignees = assignees_by_item.get(
            calendar_item_id,
            {"assignee_user_ids": [], "assignee_team_ids": []},
        )
        result_items.append(
            {key: _calendar_value_or_none(value=value) for key, value in item.items()}
        )
        result_items[-1]["exdates"] = exdates_by_item.get(calendar_item_id, [])
        result_items[-1]["assignee_user_ids"] = assignees["assignee_user_ids"]
        result_items[-1]["assignee_team_ids"] = assignees["assignee_team_ids"]

    return result_items


@router.get(
    "/calendar-categories",
    response_model=list[interfaces.CalendarItemCategoryInterface],
)
async def get_portfolio_calendar_categories(
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """Get all calendar event categories for all projects in the user's portfolio.

    Args:
        db: Async database session.
    """
    return await crud_calendar.get_calendar_item_categories(db=db)
