import re
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pandas as pd
import polars as pl

if TYPE_CHECKING:
    from fastapi.responses import Response

from sqlalchemy import MetaData, Table, TextClause, text
from sqlalchemy import exc as sa_exc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from core import models
from core.crud.operational.projects import (
    get_project_timezone_and_data_cagg_interval_by_name_short_async,
)
from core.crud.project.tags import get_project_tags
from core.enumerations import AggregationType, TimeInterval, TimeOffset
from core.model_list import ModelList
from core.utils import arrow as arrow_utils
from core.utils.pivot import pivot_timeseries_by_tag_polars

warnings.filterwarnings(
    "ignore", message="Did not recognize type 'ltree'", category=sa_exc.SAWarning
)


def _interval_to_minutes(*, interval_str: str) -> float:
    """Convert interval string to minutes for comparison.

        Parses strings like '1min', '5min', '1hour' by extracting the
        numeric portion and unit.

    Args:
        interval_str: TODO: describe.
    """
    # Extract numeric portion and unit from the interval string
    match = re.match(r"(\d+)(min|hour|sec)", interval_str.lower())
    if not match:
        raise ValueError(f"Invalid interval format: {interval_str}")

    value = int(match.group(1))
    unit = match.group(2)

    # Convert to minutes based on unit
    if unit == "sec":
        return value / 60
    elif unit == "min":
        return value
    elif unit == "hour":
        return value * 60
    else:
        raise ValueError(f"Unsupported time unit: {unit}")


@dataclass(slots=True)
class DataTimeseries:
    df: pl.DataFrame = field(default_factory=pl.DataFrame)
    df_arrow: "Response | None" = None
    page_limit_reached: bool = False

    @classmethod
    async def get(
        cls,
        *,
        # --- query-kwargs ---
        project_name_short: str,
        tag_ids: list[int] = [],
        sensor_type_ids: list[int] = [],
        query_start: datetime,
        query_end: datetime,
        max_lookback_period: TimeOffset = TimeOffset.NONE,
        agg_interval: TimeInterval = TimeInterval.FIVE_MINUTES,
        aggregation: AggregationType = AggregationType.LAST,
        pagination_limit: int = 100_000,
        pagination_offset: int = 0,
        dangerous_pagination_override: bool = False,
        # --- post-processing-kwargs ---
        project_db: Session,
        operational_db: AsyncSession,
        ffill_limit: int | None = None,
        ensure_full_range: bool = False,
        return_arrow: bool = True,
    ) -> "DataTimeseries":
        # --- Pre-Processing ---
        """TODO: add description.

        Args:
            project_name_short: TODO: describe.
            tag_ids: TODO: describe.
            sensor_type_ids: TODO: describe.
            query_start: TODO: describe.
            query_end: TODO: describe.
            max_lookback_period: TODO: describe.
            agg_interval: TODO: describe.
            aggregation: TODO: describe.
            pagination_limit: TODO: describe.
            pagination_offset: TODO: describe.
            dangerous_pagination_override: TODO: describe.
            project_db: TODO: describe.
            operational_db: TODO: describe.
            ffill_limit: TODO: describe.
            ensure_full_range: TODO: describe.
            return_arrow: TODO: describe.
        """
        self = cls()
        (
            timezone,
            interval,
            cagg_interval,
            query_start,
            query_end,
        ) = await cls._pre_process_data_timeseries(
            operational_db=operational_db,
            project_name_short=project_name_short,
            tag_ids=tag_ids,
            sensor_type_ids=sensor_type_ids,
            agg_interval=agg_interval,
            query_start=query_start,
            query_end=query_end,
        )

        # --- Build Queries ---
        max_lookback_td = pd.Timedelta(max_lookback_period.value)
        lookback_query = cls._build_lookback_query(
            project_name_short=project_name_short,
            tag_ids=tag_ids,
            sensor_type_ids=sensor_type_ids,
            cagg_interval=cagg_interval,
            query_start=query_start,
            max_lookback_period=max_lookback_td,
        )

        query = cls._build_data_timeseries_query(
            project_name_short=project_name_short,
            tag_ids=tag_ids,
            sensor_type_ids=sensor_type_ids,
            query_start=query_start,
            query_end=query_end,
            interval=interval,
            cagg_interval=cagg_interval,
            aggregation=aggregation,
            pagination_limit=pagination_limit,
            pagination_offset=pagination_offset,
            dangerous_pagination_override=dangerous_pagination_override,
        )

        # --- Execute Queries ---
        lookback_model_list: ModelList = ModelList(query=lookback_query)
        model_list: ModelList = ModelList(query=query)

        df = await model_list.polars_dataframe_async()
        lookback_df = await lookback_model_list.polars_dataframe_async()

        # --- Post-Processing ---
        df, page_limit_reached = await cls._post_process_data_timeseries(
            df=df,
            lookback_df=lookback_df,
            tag_ids=tag_ids,
            sensor_type_ids=sensor_type_ids,
            project_db=project_db,
            timezone=timezone,
            ffill_limit=ffill_limit,
            ensure_full_range=ensure_full_range,
            query_start=query_start,
            query_end=query_end,
            agg_interval=agg_interval,
            pagination_limit=pagination_limit,
            dangerous_pagination_override=dangerous_pagination_override,
        )

        self.df = df
        self.page_limit_reached = page_limit_reached

        # Return in Arrow format if requested
        if return_arrow:
            self.df_arrow = arrow_utils.polars_to_arrow_response(
                df=df,
                filename="data_timeseries.arrow",
            )

        return self

    @staticmethod
    async def _pre_process_data_timeseries(
        *,
        operational_db: AsyncSession,
        project_name_short: str,
        tag_ids: list[int],
        sensor_type_ids: list[int],
        agg_interval: TimeInterval,
        query_start: datetime,
        query_end: datetime,
    ) -> tuple[str, TimeInterval | None, TimeInterval | None, datetime, datetime]:
        """Pre-process data timeseries request.

                Fetches project info and determines whether to use continuous aggregate table.

                Returns:
                    tuple: (timezone, interval, cagg_interval)

        Args:
            operational_db: TODO: describe.
            project_name_short: TODO: describe.
            tag_ids: TODO: describe.
            sensor_type_ids: TODO: describe.
            agg_interval: TODO: describe.
            query_start: TODO: describe.
            query_end: TODO: describe.
        """
        # --- Validate Inputs ---
        if tag_ids and sensor_type_ids:
            raise ValueError("Cannot specify both 'tag_ids' and 'sensor_type_ids'.")

        if not tag_ids and not sensor_type_ids:
            raise ValueError("Must specify either 'tag_ids' or 'sensor_type_ids'.")

        # --- Fetch project info from operational_db ---
        project_info = (
            await get_project_timezone_and_data_cagg_interval_by_name_short_async(
                db=operational_db, name_short=project_name_short
            )
        )

        if project_info is None:
            raise ValueError(
                f"Project '{project_name_short}' not found in operational database"
            )

        # Get timezone from project
        timezone = project_info["timezone"]
        if timezone is None:
            raise ValueError(
                f"Project '{project_name_short}' has no timezone configured"
            )

        # Determine if we should use continuous aggregate table
        project_data_cagg_interval = project_info.get("data_cagg_interval")

        # Check if we can use cagg table:
        # - Project has a cagg interval configured
        # - Requested agg_interval >= project's cagg interval
        use_cagg = False
        if project_data_cagg_interval is not None:
            project_cagg_minutes = _interval_to_minutes(
                interval_str=project_data_cagg_interval
            )
            agg_interval_minutes = _interval_to_minutes(interval_str=agg_interval.value)
            use_cagg = agg_interval_minutes >= project_cagg_minutes

        # Set interval and cagg_interval based on logic:
        # - If using cagg and intervals match: query cagg table directly
        # - If using cagg but need larger interval: query cagg with time_bucket
        # - If not using cagg: query raw data with time_bucket
        if use_cagg:
            # Use the project's cagg interval table
            cagg_interval = TimeInterval(project_data_cagg_interval)  # type: ignore

            # If requested interval matches cagg, no time_bucket needed
            if agg_interval.value == project_data_cagg_interval:
                interval = None
            else:
                # Need to aggregate up from cagg interval to requested interval
                interval = agg_interval
        else:
            # Use raw data with time_bucket
            interval = agg_interval
            cagg_interval = None

        # Cast to datetime at microsecond level and convert to project timezone
        query_start = query_start.replace(microsecond=query_start.microsecond)
        query_end = query_end.replace(microsecond=query_end.microsecond)

        # Convert to project timezone
        project_tz = ZoneInfo(timezone)
        if query_start.tzinfo is None:
            query_start = query_start.replace(tzinfo=project_tz)
        else:
            query_start = query_start.astimezone(project_tz)

        if query_end.tzinfo is None:
            query_end = query_end.replace(tzinfo=project_tz)
        else:
            query_end = query_end.astimezone(project_tz)

        return timezone, interval, cagg_interval, query_start, query_end

    @staticmethod
    def _build_data_timeseries_query(
        *,
        project_name_short: str,
        tag_ids: list[int],
        sensor_type_ids: list[int],
        interval: TimeInterval | None,
        cagg_interval: TimeInterval | None,
        aggregation: AggregationType | None,
        query_start: datetime,
        query_end: datetime,
        pagination_limit: int = 100_000,
        pagination_offset: int = 0,
        dangerous_pagination_override: bool = False,
    ) -> TextClause:
        # --- Build schema and table in a sql-injection safe manner ---
        """TODO: add description.

        Args:
            project_name_short: TODO: describe.
            tag_ids: TODO: describe.
            sensor_type_ids: TODO: describe.
            interval: TODO: describe.
            cagg_interval: TODO: describe.
            aggregation: TODO: describe.
            query_start: TODO: describe.
            query_end: TODO: describe.
            pagination_limit: TODO: describe.
            pagination_offset: TODO: describe.
            dangerous_pagination_override: TODO: describe.
        """
        if cagg_interval:
            table_name = f"data_timeseries_{cagg_interval.value}"
        else:
            table_name = "data_timeseries"

        metadata = MetaData(schema=project_name_short)
        table = Table(
            table_name,
            metadata,
            schema=project_name_short,
        )

        # Build aggregation functions based on the aggregation type
        if aggregation == AggregationType.LAST:
            agg_functions = {
                "value_integer": "last(dt.value_integer, dt.time)",
                "value_bigint": "last(dt.value_bigint, dt.time)",
                "value_real": "last(dt.value_real, dt.time)",
                "value_double": "last(dt.value_double, dt.time)",
                "value_boolean": "last(dt.value_boolean, dt.time)",
                "value_text": "last(dt.value_text, dt.time)",
            }
        elif aggregation == AggregationType.AVERAGE:
            agg_functions = {
                "value_integer": "avg(dt.value_integer)",
                "value_bigint": "avg(dt.value_bigint)",
                "value_real": "avg(dt.value_real)",
                "value_double": "avg(dt.value_double)",
                "value_boolean": "avg(dt.value_boolean::int) > 0.5",
                "value_text": "last(dt.value_text, dt.time)",
            }
        else:
            raise ValueError(f"Unsupported aggregation type: {aggregation}")

        # S608:  SQL Injection avoided by using Table from sqlalchemy
        # Build the query based on whether we're filtering by tag_ids or sensor_type_ids
        if cagg_interval:
            time_bucket_select = "dt.time as time_bucket"
            group_by_clause = "GROUP BY dt.time, dt.tag_id"
        else:
            time_bucket_select = "time_bucket(:interval, dt.time) as time_bucket"
            group_by_clause = "GROUP BY time_bucket, dt.tag_id"

        # Conditionally add LIMIT and OFFSET clauses
        if dangerous_pagination_override:
            pagination_clause = ""
        else:
            pagination_clause = """
            LIMIT :pagination_limit
            OFFSET :pagination_offset"""

        # Declare variables before if/else to avoid mypy no-redef error
        statement: str
        bind_params: dict[str, object]

        if tag_ids:
            # Direct tag_id filtering (original behavior)
            statement = f"""
            SELECT
                {time_bucket_select},
                dt.tag_id,
                {agg_functions["value_integer"]} as value_integer,
                {agg_functions["value_bigint"]} as value_bigint,
                {agg_functions["value_real"]} as value_real,
                {agg_functions["value_double"]} as value_double,
                {agg_functions["value_boolean"]} as value_boolean,
                {agg_functions["value_text"]} as value_text
            FROM
                {table.schema}.{table.name} dt
            WHERE
                dt.time >= :query_start
                and dt.time < :query_end
                and dt.tag_id IN :filter_ids
            {group_by_clause}
            ORDER BY
                time_bucket, dt.tag_id
            {pagination_clause};
            """  # noqa: S608

            bind_params = {
                "query_start": query_start.isoformat(),
                "query_end": query_end.isoformat(),
                "filter_ids": tuple(tag_ids) if tag_ids else (),
            }
            if not dangerous_pagination_override:
                bind_params["pagination_limit"] = pagination_limit
                bind_params["pagination_offset"] = pagination_offset
            if not cagg_interval:
                bind_params["interval"] = interval
        else:
            # sensor_type_ids filtering with JOIN
            statement = f"""
            SELECT
                {time_bucket_select},
                dt.tag_id,
                {agg_functions["value_integer"]} as value_integer,
                {agg_functions["value_bigint"]} as value_bigint,
                {agg_functions["value_real"]} as value_real,
                {agg_functions["value_double"]} as value_double,
                {agg_functions["value_boolean"]} as value_boolean,
                {agg_functions["value_text"]} as value_text
            FROM
                {table.schema}.{table.name} dt
            INNER JOIN
                {project_name_short}.tags t ON dt.tag_id = t.tag_id
            WHERE
                dt.time >= :query_start
                and dt.time < :query_end
                and t.sensor_type_id IN :filter_ids
            {group_by_clause}
            ORDER BY
                time_bucket, dt.tag_id
            {pagination_clause};
            """  # noqa: S608

            bind_params = {
                "query_start": query_start.isoformat(),
                "query_end": query_end.isoformat(),
                "filter_ids": tuple(sensor_type_ids) if sensor_type_ids else (),
            }
            if not dangerous_pagination_override:
                bind_params["pagination_limit"] = pagination_limit
                bind_params["pagination_offset"] = pagination_offset
            if not cagg_interval:
                bind_params["interval"] = interval

        query: TextClause = text(statement).bindparams(**bind_params)
        return query

    @staticmethod
    def _build_lookback_query(
        *,
        project_name_short: str,
        tag_ids: list[int] = [],
        sensor_type_ids: list[int] = [],
        cagg_interval: TimeInterval | None = None,
        query_start: datetime,
        max_lookback_period: timedelta,
    ) -> TextClause:
        """Build query to get the last value before query_start for each tag.

        Args:
            project_name_short: TODO: describe.
            tag_ids: TODO: describe.
            sensor_type_ids: TODO: describe.
            cagg_interval: TODO: describe.
            query_start: TODO: describe.
            max_lookback_period: TODO: describe.
        """
        # --- Build schema and table in a sql-injection safe manner ---
        if cagg_interval:
            table_name = f"data_timeseries_{cagg_interval.value}"
        else:
            table_name = "data_timeseries"

        metadata = MetaData(schema=project_name_short)
        table = Table(
            table_name,
            metadata,
            schema=project_name_short,
        )

        # Build time constraint and bind params
        lookback_start = query_start - max_lookback_period
        bind_params_base = {
            "query_start": query_start.isoformat(),
            "lookback_start": lookback_start.isoformat(),
        }
        time_constraint = "dt.time < :query_start AND dt.time >= :lookback_start"

        if tag_ids:
            # Use DISTINCT ON for efficient last value per tag
            statement = f"""
            SELECT DISTINCT ON (dt.tag_id)
                dt.tag_id,
                dt.value_integer,
                dt.value_bigint,
                dt.value_real,
                dt.value_double,
                dt.value_boolean,
                dt.value_text
            FROM
                {table.schema}.{table.name} dt
            WHERE
                {time_constraint}
                AND dt.tag_id IN :filter_ids
            ORDER BY
                dt.tag_id, dt.time DESC;
            """  # noqa: S608

            bind_params = {
                **bind_params_base,
                "filter_ids": tuple(tag_ids) if tag_ids else (),
            }
        else:
            # sensor_type_ids filtering with JOIN
            statement = f"""
            SELECT DISTINCT ON (dt.tag_id)
                dt.tag_id,
                dt.value_integer,
                dt.value_bigint,
                dt.value_real,
                dt.value_double,
                dt.value_boolean,
                dt.value_text
            FROM
                {table.schema}.{table.name} dt
            INNER JOIN
                {project_name_short}.tags t ON dt.tag_id = t.tag_id
            WHERE
                {time_constraint}
                AND t.sensor_type_id IN :filter_ids
            ORDER BY
                dt.tag_id, dt.time DESC;
            """  # noqa: S608

            bind_params = {
                **bind_params_base,
                "filter_ids": tuple(sensor_type_ids) if sensor_type_ids else (),
            }

        query: TextClause = text(statement).bindparams(**bind_params)
        return query

    @staticmethod
    async def _post_process_data_timeseries(
        *,
        df: pl.DataFrame,
        lookback_df: pl.DataFrame,
        tag_ids: list[int],
        sensor_type_ids: list[int],
        project_db: Session,
        timezone: str,
        ffill_limit: int | None,
        ensure_full_range: bool,
        query_start: datetime,
        query_end: datetime,
        agg_interval: TimeInterval,
        pagination_limit: int,
        dangerous_pagination_override: bool,
    ) -> tuple[pl.DataFrame, bool]:
        """Post-process timeseries data: pivot, apply lookback, forward fill,
                and ensure full range.

        Args:
            df: TODO: describe.
            lookback_df: TODO: describe.
            tag_ids: TODO: describe.
            sensor_type_ids: TODO: describe.
            project_db: TODO: describe.
            timezone: TODO: describe.
            ffill_limit: TODO: describe.
            ensure_full_range: TODO: describe.
            query_start: TODO: describe.
            query_end: TODO: describe.
            agg_interval: TODO: describe.
            pagination_limit: TODO: describe.
            dangerous_pagination_override: TODO: describe.
        """
        # Check pagination limit
        if len(df) == pagination_limit and not dangerous_pagination_override:
            page_limit_reached = True
        else:
            page_limit_reached = False

        # Get tags
        if tag_ids:
            tags: pl.DataFrame = await get_project_tags(
                db=project_db,
                tag_ids=tag_ids,
                return_query=True,
            ).polars_dataframe_async()
        else:
            tags = await get_project_tags(
                db=project_db,
                sensor_type_ids=sensor_type_ids,
                return_query=True,
            ).polars_dataframe_async()

        # Pivot dataframe
        df = pivot_timeseries_by_tag_polars(
            df=df,
            tags=tags,
            project_timezone=timezone,
        )

        # Apply lookback values to first row if NaN
        if len(lookback_df) > 0 and len(df) > 0:
            # Add dummy time column for pivot function (lookback has one value per tag)
            # Use first time from main df
            first_time = df.select("time").item(0, 0)
            lookback_df = lookback_df.with_columns(pl.lit(first_time).alias("time"))
            # Pivot lookback data to match df structure
            lookback_pivoted = pivot_timeseries_by_tag_polars(
                df=lookback_df,
                tags=tags,
                project_timezone=timezone,
            )

            # Replace first row NaN values with lookback values using
            # polars operations. Filter out time-related columns and only
            # keep columns that exist in both dataframes
            lookback_cols = [
                col
                for col in lookback_pivoted.columns
                if col not in ["time", "time_bucket"] and col in df.columns
            ]
            df = df.with_columns(
                [
                    pl.when(pl.int_range(pl.len()) == 0)
                    .then(
                        pl.when(pl.col(col).is_null())
                        .then(
                            pl.lit(lookback_pivoted[col].item())
                        )  # Extract scalar value
                        .otherwise(pl.col(col))
                    )
                    .otherwise(pl.col(col))
                    .alias(col)
                    for col in lookback_cols
                ]
            )

        # Get time column name (could be 'time' or 'time_bucket')
        time_col = "time" if "time" in df.columns else "time_bucket"

        # Ensure full range if requested
        if ensure_full_range and len(df) > 0:
            # Create complete time range
            interval_td = pd.Timedelta(agg_interval.value)

            full_range = pd.date_range(
                start=query_start,
                end=query_end,
                freq=interval_td,
                inclusive="left",
            )

            full_range_df = pl.DataFrame({time_col: full_range}).with_columns(
                pl.col(time_col).dt.cast_time_unit("us")
            )
            df = df.with_columns(pl.col(time_col).dt.cast_time_unit("us"))
            df = full_range_df.join(
                df,
                on=time_col,
                how="left",
            )

        # Forward fill nulls only up to current time (not beyond now)
        # Convert now to project timezone to match the time column timezone
        now = datetime.now(ZoneInfo(timezone))

        # For each data column, only forward fill if row timestamp <= now
        data_cols = [c for c in df.columns if c not in [time_col, "time"]]
        df = df.with_columns(
            [
                pl.when(pl.col(time_col).dt.convert_time_zone(timezone) <= pl.lit(now))
                .then(pl.col(col).fill_null(strategy="forward", limit=ffill_limit))
                .otherwise(pl.col(col))
                .alias(col)
                for col in data_cols
            ]
        )

        return df, page_limit_reached


# --- THIS FUNCTION IS DEPRECATED ---
# Please use the v3 function instead
def get_project_data_timeseries(
    project_db: Session,
    *,
    project_name_short: str,
    tag_ids: list[int],
    start: pd.Timestamp,
    end: pd.Timestamp,
    interval: str,
    cagg_interval: str | None = None,
) -> ModelList[models.DataTimeseries]:
    """TODO: add description.

    Args:
        project_db: TODO: describe.
        project_name_short: TODO: describe.
        tag_ids: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        interval: TODO: describe.
        cagg_interval: TODO: describe.
    """
    if cagg_interval:
        table_name = f"data_timeseries_{cagg_interval}"
    else:
        table_name = "data_timeseries"

    metadata = MetaData(schema=project_name_short)
    table = Table(
        table_name,
        metadata,
        schema=project_name_short,
        autoload_with=project_db.bind,
    )

    # S608:  SQL Injection should be avoided by matching table name to schema above
    #   Tested with: Non-valid table_names, instructions
    #   and even partially valid table_names
    #   This approach (using autoload_with) causes two round trips to the database
    #   and is not recommended since using Table by itself should prevent SQL injection.
    statement = f"""
    SELECT
        time_bucket(:interval, time) + interval :interval as time_bucket,
        tag_id,
        last(value_integer, time) as value_integer,
        last(value_bigint, time) as value_bigint,
        last(value_real, time) as value_real,
        last(value_double, time) as value_double,
        last(value_boolean, time) as value_boolean,
        last(value_text, time) as value_text
    FROM
        {table.schema}.{table.name}
    WHERE
        time >= :start and time < :end and tag_id IN :tag_ids
    GROUP BY
        time_bucket, tag_id
    ORDER BY
        time_bucket, tag_id;
    """  # noqa: S608

    result = project_db.execute(
        text(statement).bindparams(
            interval=interval,
            start=start.isoformat(),
            end=end.isoformat(),
            tag_ids=tuple(tag_ids),
        ),
    )

    return ModelList(result=result, model_cls=models.DataTimeseries)
