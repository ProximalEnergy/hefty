from typing import Annotated, Any
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import core
from app import dependencies, interfaces, utils
from app._crud.operational import calendar as crud_calendar
from app._crud.operational.data_timeseries import get_operational_data_timeseries
from app.interfaces import CalendarItem, UserData

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"],
    include_in_schema=utils.get_include_in_schema(),
)


class PortfolioHome(BaseModel):
    project_id: UUID
    power: float | None
    poa: float | None
    soc: float | None
    times: list[Any] | None
    meter_active_power: list[Any] | None
    meter_soc_percent: list[Any] | None


@router.get(
    "/home",
    response_model=list[PortfolioHome],
    response_class=ORJSONResponse,
)
async def get_home(
    project_ids: Annotated[list[UUID] | None, Query()] = None,
    db: AsyncSession = Depends(dependencies.get_async_db),
    user_data: interfaces.UserData = Depends(dependencies.get_user_data_async),
):
    # If project_ids is not provided, default to all projects the user has access to
    if project_ids is None:
        project_ids = user_data.operational_project_ids
    # If project_ids is provided, ensure they are within the user's access list
    else:
        project_ids = list(set(project_ids) & set(user_data.operational_project_ids))

    projects = await core.crud.operational.projects.get_projects_async(
        db, project_ids=project_ids
    )
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

        # Raise an error if the DataFrame is empty
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail="No portfolio data found for the past 24 hours.",
            )

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

        # Raise an error if the DataFrame is empty
        if df_day_behind.empty:
            raise HTTPException(
                status_code=404,
                detail="No portfolio data found for the past 24 hours.",
            )

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
        df_project = df[df["project_id"] == project_id]

        if df_project.empty:
            return_data.append(
                PortfolioHome(
                    project_id=project_id,
                    power=None,
                    poa=None,
                    soc=None,
                    times=None,
                    meter_active_power=None,
                    meter_soc_percent=None,
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

            return_data.append(
                PortfolioHome(
                    project_id=project_id,
                    power=power,
                    poa=poa,
                    soc=soc,
                    times=times,
                    meter_active_power=meter_active_power,
                    meter_soc_percent=meter_soc_percent,
                ),
            )

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
