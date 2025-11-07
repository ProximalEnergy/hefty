from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import core
from app import dependencies, interfaces, utils
from app._crud.operational import calendar as crud_calendar
from app._crud.operational.data_timeseries import get_operational_data_timeseries
from app._crud.operational.kpi_data import get_kpi_data_async
from app.interfaces import CalendarItem, UserData

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"],
    include_in_schema=utils.get_include_in_schema(),
)


class PortfolioHomeShortTerm(BaseModel):
    project_id: UUID
    power: float | None
    poa: float | None
    soc: float | None
    times: list[Any] | None
    meter_active_power: list[Any] | None
    meter_soc_percent: list[Any] | None
    max_charge_power: list[Any] | None
    max_discharge_power: list[Any] | None


class PortfolioHomeLongTerm(BaseModel):
    project_id: UUID
    times: list[Any] | None
    cycle_count_string: list[Any] | None
    state_of_health: list[Any] | None
    pcs_mechanical_availability: list[Any] | None
    energy_production: list[Any] | None


class PortfolioHome(PortfolioHomeShortTerm, PortfolioHomeLongTerm):
    pass


class TimeFrame(StrEnum):
    H24 = "24h"
    D30 = "30d"


async def get_portfolio_home_short_term(
    project_ids: list[UUID],
    db: AsyncSession,
) -> list[PortfolioHomeShortTerm]:
    if len(project_ids) == 0:
        return []

    projects_ml = await core.crud.operational.projects.get_projects_async(
        db=db, project_ids=project_ids
    )
    projects = projects_ml.models()
    projects_df = pd.DataFrame([x.__dict__ for x in projects]).set_index("project_id")

    real_time_project_ids = [x.project_id for x in projects if x.has_real_time_data]
    day_behind_project_ids = [
        x.project_id for x in projects if not x.has_real_time_data
    ]

    # end equal to current time in utc
    end = pd.Timestamp.utcnow().floor("5min")

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
            with pd.option_context("future.no_silent_downcasting", True):
                df["value"] = df.filter(regex="value_").bfill(axis=1).iloc[:, 0]
            df = df.infer_objects()

            # Select the relevant columns
            df = df[["time", "project_id", "tag_id", "sensor_type_id", "value"]]

    if day_behind_project_ids:
        day_behind_start = (
            start.tz_convert(
                projects_df.loc[day_behind_project_ids, "time_zone"].values[0]  # type: ignore
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
            with pd.option_context("future.no_silent_downcasting", True):
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
                    (df_project[max_charge_columns].sum(axis=1) / -1_000)
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
                    (df_project[max_discharge_columns].sum(axis=1) / 1_000)
                    .clip(upper=poi)
                    .tolist()
                )
            else:
                max_discharge_power = None

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
                ),
            )

    return return_data


async def get_portfolio_home_long_term(
    project_ids: list[UUID],
    db: AsyncSession,
) -> list[PortfolioHomeLongTerm]:
    if len(project_ids) == 0:
        return []

    # KPI type IDs for long-term data
    # 32 = cycle_count_string (BESS_STRING_CYCLE_COUNT)
    # 54 = state_of_health (BESS_STRING_SOH)
    # 1 = pcs_mechanical_availability
    # 2 = energy_production
    kpi_type_ids = [32, 54, 1, 2]

    # end equal to current date in UTC
    end_date = pd.Timestamp.utcnow().floor("D").date()

    # start equal to end minus 30 days
    start_date = (pd.Timestamp.utcnow().floor("D") - pd.Timedelta(days=30)).date()

    # Query KPI data
    kpi_df = await get_kpi_data_async(
        db,
        start=start_date,
        end=end_date,
        project_ids=project_ids,
        kpi_type_ids=kpi_type_ids,
        include_device_data=False,
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
                df_pivot[1].tolist() if 1 in df_pivot.columns else None
            )
            energy_production = df_pivot[2].tolist() if 2 in df_pivot.columns else None

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
    "/home",
    response_model=list[PortfolioHome],
    response_class=ORJSONResponse,
)
async def get_home(
    project_ids: Annotated[list[UUID] | None, Query()] = None,
    db: AsyncSession = Depends(dependencies.get_async_db),
    user_data: interfaces.UserData = Depends(dependencies.get_user_data_async),
    time: TimeFrame = Query(default=TimeFrame.H24),  # new parameter
):
    # If project_ids is not provided, default to all projects the user has access to
    if project_ids is None:
        project_ids = user_data.operational_project_ids
    # If project_ids is provided, ensure they are within the user's access list
    else:
        project_ids = list(set(project_ids) & set(user_data.operational_project_ids))

    if time.value == TimeFrame.H24.value:
        short_term_data = await get_portfolio_home_short_term(project_ids, db)
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
                # Long-term fields set to None
                cycle_count_string=None,
                state_of_health=None,
                pcs_mechanical_availability=None,
                energy_production=None,
            )
            for item in short_term_data
        ]
    else:
        long_term_data = await get_portfolio_home_long_term(project_ids, db)
        # Convert long-term data to PortfolioHome format
        return_data = [
            PortfolioHome(
                project_id=item.project_id,
                # Short-term fields set to None
                power=None,
                poa=None,
                soc=None,
                times=item.times,
                meter_active_power=None,
                meter_soc_percent=None,
                max_charge_power=None,
                max_discharge_power=None,
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
    response_model=list[CalendarItem],
)
async def get_portfolio_calendar_events(
    project_ids: Annotated[list[UUID] | None, Query()] = None,
    user_data: UserData = Depends(dependencies.get_user_data_async),
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """
    Get all calendar events for all projects in the user's portfolio.
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

    # Fetch calendar items and all their related data in a single, efficient query
    # NOTE: This requires updating your `crud_calendar.get_calendar_items` function.
    # See the "Required Change" section below for details.
    calendar_items_from_db = await crud_calendar.get_calendar_items(
        db=db, project_ids=accessible_project_ids
    )

    # Shape the data into the final response model
    result_items = []
    for item in calendar_items_from_db:
        result_items.append(
            {
                # Include all direct fields from the ORM object
                **{c.name: getattr(item, c.name) for c in item.__table__.columns},
                # Add fields from eagerly loaded relationships
                "color": item.category.color_code if item.category else None,
                "exdates": [
                    exc.exception_date.isoformat()
                    for exc in item.exceptions
                    if exc.is_cancelled
                ],
                "assignee_user_ids": [
                    a.user_id for a in item.assignments if a.user_id is not None
                ],
                "assignee_team_ids": [
                    a.team_id for a in item.assignments if a.team_id is not None
                ],
            }
        )

    return result_items


@router.get(
    "/calendar-categories",
    response_model=list[interfaces.CalendarItemCategory],
)
async def get_portfolio_calendar_categories(
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """
    Get all calendar event categories for all projects in the user's portfolio.
    """
    return await crud_calendar.get_calendar_item_categories(db=db)
