import re
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, overload
from zoneinfo import ZoneInfo

import clickhouse_connect
import numpy as np
import pandas as pd
import polars as pl
from polars.datatypes import Boolean, String
from sqlalchemy import MetaData, Table, TextClause, select, text
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import Session, load_only

from core import models, settings
from core.crud.project.tags import get_project_tags_v2
from core.db_query import OutputType
from core.dependencies import get_db_session_async
from core.enumerations import (
    AggregationMethod,
    ProjectDatabaseProvider,
    TimeInterval,
    TimeOffset,
)
from core.model_list import ModelList

try:
    from fastapi import HTTPException

    FASTAPI_INSTALLED = True
except ImportError:
    FASTAPI_INSTALLED = False

warnings.filterwarnings(
    "ignore", message="Did not recognize type 'ltree'", category=sa_exc.SAWarning
)


class FilterMethod(Enum):
    TAG_IDS = "tag_ids"
    TAG_POLARS = "tag_polars"
    SENSOR_TYPE_IDS = "sensor_type_ids"


PG_DATA_TYPE_ID_TO_VALUE_COL: dict[int, str] = {
    1: "value_integer",
    2: "value_bigint",
    3: "value_real",
    4: "value_double",
    5: "value_boolean",
    6: "value_text",
}


@dataclass(slots=True, init=False)
class DataTimeseries:
    # Required fields, must be provided in constructor
    project_name_short: str
    filter_method: FilterMethod
    filter_values: list[int] | pl.DataFrame
    query_start: datetime
    query_end: datetime
    project_db: Session

    # Optional fields (with defaults)
    max_lookback_period: TimeOffset = TimeOffset.FIVE_MINUTES
    freq: TimeInterval = TimeInterval.FIVE_MINUTES
    aggregation_method: AggregationMethod = AggregationMethod.FIRST
    pagination_limit: int = 100_000
    pagination_offset: int = 0
    dangerous_pagination_override: bool = False
    ffill_limit: int | None = None
    ensure_full_range: bool = True
    apply_scale_and_offset: bool = True

    # Internal fields (set during execution, not in constructor)
    _tag_ids: list[int] = field(default_factory=list)
    _tags_lut: pl.DataFrame = field(default_factory=pl.DataFrame)
    _time_zone: str = ""
    _data_cagg_interval: str | None = None
    _project_id_int: int = 0
    _database_provider: ProjectDatabaseProvider | None = None

    # Public fields (set during execution)
    df: pl.DataFrame = field(default_factory=pl.DataFrame)
    page_limit_reached: bool = False

    @overload
    def __init__(
        self,
        *,
        project_name_short: str,
        filter_method: Literal[FilterMethod.TAG_IDS],
        filter_values: list[int],
        query_start: datetime,
        query_end: datetime,
        project_db: Session,
        max_lookback_period: TimeOffset = ...,
        freq: TimeInterval = ...,
        aggregation_method: AggregationMethod = ...,
        pagination_limit: int = ...,
        pagination_offset: int = ...,
        dangerous_pagination_override: bool = ...,
        ffill_limit: int | None = ...,
        ensure_full_range: bool = ...,
        apply_scale_and_offset: bool = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        project_name_short: str,
        filter_method: Literal[FilterMethod.SENSOR_TYPE_IDS],
        filter_values: list[int],
        query_start: datetime,
        query_end: datetime,
        project_db: Session,
        max_lookback_period: TimeOffset = ...,
        freq: TimeInterval = ...,
        aggregation_method: AggregationMethod = ...,
        pagination_limit: int = ...,
        pagination_offset: int = ...,
        dangerous_pagination_override: bool = ...,
        ffill_limit: int | None = ...,
        ensure_full_range: bool = ...,
        apply_scale_and_offset: bool = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *,
        project_name_short: str,
        filter_method: Literal[FilterMethod.TAG_POLARS],
        filter_values: pl.DataFrame,
        query_start: datetime,
        query_end: datetime,
        project_db: Session,
        max_lookback_period: TimeOffset = ...,
        freq: TimeInterval = ...,
        aggregation_method: AggregationMethod = ...,
        pagination_limit: int = ...,
        pagination_offset: int = ...,
        dangerous_pagination_override: bool = ...,
        ffill_limit: int | None = ...,
        ensure_full_range: bool = ...,
        apply_scale_and_offset: bool = ...,
    ) -> None: ...

    def __init__(
        self,
        *,
        project_name_short: str,
        filter_method: FilterMethod,
        filter_values: list[int] | pl.DataFrame,
        query_start: datetime,
        query_end: datetime,
        project_db: Session,
        max_lookback_period: TimeOffset = TimeOffset.FIVE_MINUTES,
        freq: TimeInterval = TimeInterval.FIVE_MINUTES,
        aggregation_method: AggregationMethod = AggregationMethod.FIRST,
        pagination_limit: int = 100_000,
        pagination_offset: int = 0,
        dangerous_pagination_override: bool = False,
        ffill_limit: int | None = None,
        ensure_full_range: bool = True,
        apply_scale_and_offset: bool = True,
    ) -> None:
        # Initialize all fields from parameters
        # (dataclass fields with defaults are initialized automatically)
        self.project_name_short = project_name_short
        self.filter_method = filter_method
        self.filter_values = filter_values
        self.query_start = query_start
        self.query_end = query_end
        self.project_db = project_db
        self.max_lookback_period = max_lookback_period
        self.freq = freq
        self.aggregation_method = aggregation_method
        self.pagination_limit = pagination_limit
        self.pagination_offset = pagination_offset
        self.dangerous_pagination_override = dangerous_pagination_override
        self.ffill_limit = ffill_limit
        self.ensure_full_range = ensure_full_range
        self.apply_scale_and_offset = apply_scale_and_offset
        # Internal and public fields with defaults are already set by
        # dataclass field definitions

    async def get(self) -> "DataTimeseries":
        """Execute the timeseries query using constructor parameters.

        Returns:
            Self with df, and page_limit_reached populated.
        """
        # Step 1: Load project metadata from operational database
        # Result: Sets _time_zone, _data_cagg_interval, _project_id_int,
        # and _database_provider
        await self._load_project_details()

        # Step 2: Normalize query_start and query_end to project timezone
        # Result: Updates self.query_start and self.query_end to be timezone-aware
        # Ensures timestamps are in the correct timezone before querying
        self._clean_query_range()

        # Step 3: Resolve filter_values to actual tag_ids based on filter_method
        # Result: Sets self._tag_ids (list of tag IDs) and self._tags_lut (lookup table)
        await self._load_tags()

        # Step 4: Early return if no tag_ids are provided
        if not hasattr(self, "_tag_ids") or (
            hasattr(self, "_tag_ids") and len(self._tag_ids) == 0
        ):
            warnings.warn("No tag_ids found, returning empty DataFrame")
            # Construct an empty DataFrame with just a "time" column of correct type
            self.df = pl.DataFrame(
                {
                    "time": pl.Series(
                        name="time",
                        values=[],
                        dtype=pl.Datetime(
                            "us",
                            time_zone=self._time_zone
                            if hasattr(self, "_time_zone")
                            else None,
                        ),
                    )
                }
            )
            return self

        # Step 5: Execute query based on database provider
        # Result: Populates self.df, self.page_limit_reached, and optionally
        if self._database_provider is None:
            raise ValueError("database_provider must be set")
        match self._database_provider:
            case ProjectDatabaseProvider.TIMESCALE:
                await self._get_timescale()
            case ProjectDatabaseProvider.CLICKHOUSE:
                await self._get_clickhouse()

        # Step 6: Return self with all data populated
        # Result: Instance ready for use with df, and page_limit_reached set
        return self

    def raise_on_empty_df(self):
        if not FASTAPI_INSTALLED:
            raise RuntimeError("fastapi not installed")
        elif self.df.is_empty():
            raise HTTPException(status_code=400, detail="No data found")

    async def _get_timescale(self) -> None:
        """Get timeseries data from Timescale."""

        # Step 1: Validate required internal state
        if not self._time_zone:
            raise ValueError("time_zone must be set")

        # Step 2: Determine which table to query and what SQL query interval to use
        table, interval_sql = self._build_table_and_interval_sql_timescale()

        # Step 3: Build lookback query to get last known values before query_start
        # Result: SQL TextClause query that fetches the most recent value per tag
        # within max_lookback_period window before query_start
        # Purpose: Used to fill NaN values at the start of the time range
        lookback_query = self._build_lookback_query_timescale(
            table_name=table,
        )

        # Step 4: Build main timeseries query
        # Result: SQL TextClause query that fetches aggregated timeseries data
        # with time bucketing, aggregation functions, and pagination
        query = self._build_data_timeseries_query_timescale(
            table_name=table,
            interval_sql=interval_sql,
        )

        # Step 5: Execute both queries asynchronously
        # Result: Two Polars DataFrames
        # - df: Main timeseries data (time, tag_id, value_* columns)
        # - lookback_df: Last known values before query_start (one row per tag)
        lookback_model_list: ModelList = ModelList(query=lookback_query)
        model_list: ModelList = ModelList(query=query)

        df = await model_list.polars_dataframe_async()
        lookback_df = await lookback_model_list.polars_dataframe_async()

        # Step 6: Post-process the data (pivot, apply lookback, forward fill, etc.)
        # Result: Processed DataFrame in wide format (time index, tag_id columns)
        # and page_limit_reached boolean flag
        df, page_limit_reached = await self._post_process_data_timeseries(
            df=df,
            lookback_df=lookback_df,
        )

        # Step 7: Store results in instance attributes
        # Result: self.df and self.page_limit_reached are now populated
        self.df = df
        self.page_limit_reached = page_limit_reached

    async def _get_clickhouse(self) -> None:
        """Execute timeseries query for ClickHouse.

        Uses instance attributes set by constructor and previous methods.
        """
        # Step 1: Validate required internal state
        # Result: Ensures project_id_int and time_zone are set (runtime safety)
        if not self._project_id_int:
            raise ValueError("project_id_int must be set")
        if not self._time_zone:
            raise ValueError("time_zone must be set")

        # Step 2: Determine SQL query interval to use
        interval_sql = self._build_interval_sql_clickhouse()

        # Step 3: Build lookback query to get last known values before query_start
        # Result: Raw SQL string query for ClickHouse
        # Purpose: Fetches most recent value per tag within max_lookback_period
        lookback_query = self._build_lookback_query_clickhouse()

        # Step 4: Build main timeseries query
        # Result: Raw SQL string query for ClickHouse with aggregation and time
        # bucketing
        query = self._build_data_timeseries_query_clickhouse(
            interval_sql=interval_sql,
        )

        # Step 5: Get ClickHouse client connection
        # Result: Client instance configured with connection settings from core.settings
        client = self._get_clickhouse_client()

        # Step 6: Execute both queries and get results as Polars DataFrames
        # Result: Two Polars DataFrames
        # - df: Main timeseries data (time_bucket, tag_id, value_* columns)
        # - lookback_df: Last known values before query_start (one row per tag)
        df = client.query_df_arrow(
            query,
            dataframe_library="polars",
        )
        lookback_df = client.query_df_arrow(
            lookback_query,
            dataframe_library="polars",
        )

        # Step 7: Normalize time column format
        # Result: DataFrame with "time" column and converted to datetime if it was a
        # Unix timestamp
        df = df.rename({"time_bucket": "time"})
        if not isinstance(df["time"].dtype, pl.Datetime):
            # ClickHouse returns Unix timestamps (seconds) - convert to datetime
            df = df.with_columns(
                pl.from_epoch(pl.col("time"), time_unit="s").alias("time")
            )

        # Step 8: Post-process the data (pivot, apply lookback, forward fill, etc.)
        # Result: Processed DataFrame in wide format and page_limit_reached flag
        df, page_limit_reached = await self._post_process_data_timeseries(
            df=df,
            lookback_df=lookback_df,
        )

        # Step 9: Store results in instance attributes
        # Result: self.df and self.page_limit_reached are now populated
        self.df = df
        self.page_limit_reached = page_limit_reached

    # -- DATABASE PROVIDER NAIVE HELPERS -- #

    async def _post_process_data_timeseries(
        self,
        *,
        df: pl.DataFrame,
        lookback_df: pl.DataFrame,
    ) -> tuple[pl.DataFrame, bool]:
        """Post-process timeseries data: pivot, apply lookback, forward fill,
                and ensure full range.

        Uses instance attributes for configuration: project_db, _time_zone,
        ffill_limit, ensure_full_range, query_start, query_end, freq,
        pagination_limit, dangerous_pagination_override.

        Args:
            df: Raw timeseries data from the main query.
            lookback_df: Last-known values prior to query_start.
        """
        # Step 1: Check if pagination limit was reached
        # If result size equals limit AND override is enabled, we hit the limit, meaning
        # there may be more data available
        if len(df) == self.pagination_limit and not self.dangerous_pagination_override:
            page_limit_reached = True
        else:
            page_limit_reached = False

        # Step 2: Pivot from long format to wide format
        # Input: Long format (time, tag_id, value_integer, value_real, ...)
        # Result: Wide format (time index, one column per tag_id), applied unit
        # scaling/offset
        df = self._pivot_timeseries_by_tag_polars(
            df=df,
        )

        # Step 3: Identify time column name (handles both 'time' and 'time_bucket')
        # Result: String with column name to use for time operations
        time_col = "time" if "time" in df.columns else "time_bucket"

        # Step 4: Ensure full time range coverage if requested
        # Result: DataFrame with rows for every timestamp in [query_start, query_end)
        if self.ensure_full_range and len(df) > 0:
            # Step 4a: Create complete time range using pandas date_range
            # Result: DatetimeIndex with all timestamps at the specified frequency
            interval_td = pd.Timedelta(self.freq.value).to_pytimedelta()

            full_range = pl.datetime_range(
                start=self.query_start,
                end=self.query_end,
                interval=interval_td,
                closed="left",
                eager=True,
            )

            # Step 4b: Convert to Polars DataFrame and normalize time unit
            # Result: DataFrame with time column in microseconds (matching df format)
            full_range_df = pl.DataFrame({time_col: full_range}).with_columns(
                pl.col(time_col).dt.cast_time_unit("us")
            )

            # Step 4c: Normalize df time column to microseconds for join compatibility
            # Result: df time column now in microseconds
            df = df.with_columns(pl.col(time_col).dt.cast_time_unit("us"))

            # Step 4d: Left join full_range with df to fill gaps
            # Result: DataFrame with all timestamps, null values where data is missing
            df = full_range_df.join(
                df,
                on=time_col,
                how="left",
            )

        # Step 5: Apply lookback values to fill NaN at the start of time range
        # Purpose: If first data point is NaN, use the last known value before
        # query_start
        # Result: First row of df has NaN values replaced with lookback values where
        # available
        if len(lookback_df) > 0 and len(df) > 0:
            # Step 5a: Add time column to lookback_df so it can be pivoted
            # Lookback data has one value tag (no time), use query_start
            # Result: lookback_df now has time column matching query_start
            lookback_df = lookback_df.with_columns(
                pl.lit(self.query_start).alias("time")
            )

            # Step 5b: Pivot lookback data to match main df structure
            # Result: lookback_pivoted has same columns as df (time + tag_id columns)
            lookback_pivoted = self._pivot_timeseries_by_tag_polars(
                df=lookback_df,
            )

            # Step 5c: Identify which columns to update (exclude time columns)
            # Result: List of tag_id column names that exist in both dataframes
            lookback_cols = [
                col
                for col in lookback_pivoted.columns
                if col not in ["time", "time_bucket"] and col in df.columns
            ]

            # Step 5d: Replace first row NaN values with lookback values
            # Logic: For each column, if first row (index 0) is null, use lookback value
            # Result: df with first row NaN values filled from lookback where available
            df = df.with_columns(
                [
                    pl.when(pl.int_range(pl.len()) == 0)  # If row index is 0
                    .then(
                        pl.when(pl.col(col).is_null())  # And column value is null
                        .then(
                            pl.lit(lookback_pivoted[col].item())  # Use lookback value
                        )
                        .otherwise(pl.col(col))  # Otherwise keep existing value
                    )
                    .otherwise(pl.col(col))  # For all other rows, keep existing value
                    .alias(col)
                    for col in lookback_cols
                ]
            )

        # Step 6: Forward fill null values, but only up to current time
        # Purpose: Fill missing values by carrying last known value forward
        # BUT don't fill future timestamps (beyond "now")

        # Step 6a: Get current time in project timezone for comparison
        now = datetime.now(ZoneInfo(self._time_zone))

        # Step 6b: Identify data columns (exclude time columns)
        data_cols = [c for c in df.columns if c not in [time_col, "time"]]

        # Step 6c: Apply forward fill with time-based condition
        # Result: DataFrame with forward-filled values up to current time
        df = df.with_columns(
            [
                pl.when(
                    pl.col(time_col).dt.convert_time_zone(self._time_zone)
                    <= pl.lit(now)  # Only fill if timestamp is in the past
                )
                .then(pl.col(col).fill_null(strategy="forward", limit=self.ffill_limit))
                .otherwise(pl.col(col))  # Keep null for future timestamps
                .alias(col)
                for col in data_cols
            ]
        )

        return df, page_limit_reached

    # -- TIMESCALE HELPERS -- #

    def _build_table_and_interval_sql_timescale(
        self,
    ) -> tuple[str, TimeInterval | None]:
        """Determine which table to query and what SQL query interval to use.

        Args:
            data_cagg_interval: Continuous aggregate interval from project config.

        Returns:
            Tuple of (table_name, interval_sql).
        """
        # Step 1: Determine table name based on continuous aggregate configuration
        # Result: Either "data_timeseries" (raw) or "data_timeseries_1min" (CAGG)
        if self._data_cagg_interval is None:
            # No CAGG: use raw data table
            table = "data_timeseries"
            interval_sql = self.freq
        else:
            # CAGG exists: use pre-aggregated 1-minute table
            # NOTE: Currently, we only have 1-minute CAGG
            table = "data_timeseries_1min"

            # Step 2: Determine if we need additional aggregation
            # If user wants > 1min intervals, we aggregate the 1min cagg data
            # If user wants <= 1min, we return raw 1min data (no aggregation)
            if self._interval_to_minutes(interval_str=self.freq) > 1:
                interval_sql = self.freq  # Need to aggregate further
            else:
                interval_sql = None  # Use raw 1min data as-is

        # Step 3: Return table name and interval SQL
        return table, interval_sql

    def _build_lookback_query_timescale(
        self,
        *,
        table_name: str,
    ) -> TextClause:
        """Build query to get the last value before query_start for each tag.

        Uses instance attributes: project_name_short, query_start,
        max_lookback_period, _tag_ids.

        Args:
            table_name: Table name to query.
        """
        # Step 1: Create SQLAlchemy Table object with proper schema
        # Result: Table object representing the timeseries table in project schema
        metadata = MetaData(schema=self.project_name_short)
        table = Table(
            table_name,
            metadata,
            schema=self.project_name_short,
        )

        # Step 2: Calculate lookback time window
        # Defines the time window to search for prior values
        max_lookback_td = pd.Timedelta(self.max_lookback_period.value)
        lookback_start = self.query_start - max_lookback_td

        # Step 3: Build time constraint SQL and bind parameters
        time_constraint = "dt.time < :query_start AND dt.time >= :lookback_start"
        bind_params = {
            "query_start": self.query_start.isoformat(),
            "lookback_start": lookback_start.isoformat(),
            "filter_ids": tuple(self._tag_ids),
        }

        # Step 4: Build SQL query using DISTINCT ON for efficiency
        # Purpose: Get the most recent value per tag within the lookback window
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

        # Step 5: Create SQLAlchemy TextClause with bound parameters
        # Result: Executable SQL query object ready for execution
        query: TextClause = text(statement).bindparams(**bind_params)

        return query

    def _build_data_timeseries_query_timescale(
        self,
        *,
        table_name: str,
        interval_sql: TimeInterval | None,
    ) -> TextClause:
        """Build the SQL query for timeseries data retrieval.

        Uses instance attributes: project_name_short, aggregation_method, query_start,
        query_end, pagination_limit, pagination_offset,
        dangerous_pagination_override, _tag_ids.

        Args:
            table_name: Table name to query.
            interval_sql: Time bucket interval for aggregation_method (computed).
        """

        # Step 1: Convert datetime objects to ISO format strings for SQL binding
        # Result: String representations of query_start and query_end timestamps
        query_start_str = self.query_start.isoformat()
        query_end_str = self.query_end.isoformat()

        # Step 2: Create SQLAlchemy Table object with proper schema
        # Purpose: Ensures SQL injection safety by using Table metadata
        # Result: Table object representing the timeseries table in project schema
        metadata = MetaData(schema=self.project_name_short)
        table = Table(
            table_name,
            metadata,
            schema=self.project_name_short,
        )

        # Step 3: Build SQL for aggregation functions based on aggregation type
        # Result: Dictionary mapping value column names to their aggregation SQL
        match self.aggregation_method:
            case AggregationMethod.FIRST:
                agg_functions = {
                    "value_integer": "first(dt.value_integer, dt.time)",
                    "value_bigint": "first(dt.value_bigint, dt.time)",
                    "value_real": "first(dt.value_real, dt.time)",
                    "value_double": "first(dt.value_double, dt.time)",
                    "value_boolean": "first(dt.value_boolean, dt.time)",
                    "value_text": "first(dt.value_text, dt.time)",
                }
            case AggregationMethod.AVERAGE:
                agg_functions = {
                    "value_integer": "avg(dt.value_integer)",
                    "value_bigint": "avg(dt.value_bigint)",
                    "value_real": "avg(dt.value_real)",
                    "value_double": "avg(dt.value_double)",
                    "value_boolean": "avg(dt.value_boolean::int) > 0.5",
                    "value_text": "first(dt.value_text, dt.time)",
                }

        # Step 4: Build time bucketing SQL based on whether aggregation is needed
        # Result: SQL expressions for time_bucket column and GROUP BY clause
        # If interval_sql exists: Use time_bucket() function to aggregate by time
        # intervals
        # If interval_sql is None: Use raw time values (no aggregation)
        if interval_sql:
            time_bucket_select = "time_bucket(:interval, dt.time) as time_bucket"
            group_by_clause = "GROUP BY time_bucket, dt.tag_id"
        else:
            time_bucket_select = "dt.time as time_bucket"
            group_by_clause = "GROUP BY time_bucket, dt.tag_id"

        # Step 5: Build pagination clause conditionally
        if self.dangerous_pagination_override:
            pagination_clause = ""
        else:
            pagination_clause = "LIMIT :pagination_limit OFFSET :pagination_offset"

        # Step 6: Declare variables before if/else to avoid mypy no-redef error
        statement: str
        bind_params: dict[str, object]

        # Step 7: Build main SELECT statement with tag filtering
        # Result: Complete SQL query string with all clauses
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

        # Step 8: Build bind parameters dictionary
        # Result: Dict with all SQL parameter values for safe parameterized query
        bind_params = {
            "query_start": query_start_str,
            "query_end": query_end_str,
            "filter_ids": tuple(self._tag_ids),
        }
        # Add pagination params if not overridden
        if not self.dangerous_pagination_override:
            bind_params["pagination_limit"] = self.pagination_limit
            bind_params["pagination_offset"] = self.pagination_offset
        # Add interval param if time bucketing is used
        if interval_sql:
            bind_params["interval"] = interval_sql

        # Step 9: Create SQLAlchemy TextClause with bound parameters
        # Result: Executable SQL query object ready for execution
        query: TextClause = text(statement).bindparams(**bind_params)

        return query

    # -- CLICKHOUSE HELPERS -- #

    def _build_interval_sql_clickhouse(self) -> TimeInterval | None:
        # Identify interval_sql, return TimeInterval if freq > 1min, else None
        if self._interval_to_minutes(interval_str=self.freq) > 1:
            return self.freq
        else:
            return None

    def _build_data_timeseries_query_clickhouse(
        self,
        *,
        interval_sql: TimeInterval | None,
    ) -> str:
        """Build ClickHouse query for data timeseries.

        Uses instance attributes: _project_id_int, _tag_ids, aggregation_method,
        query_start, query_end, pagination_limit, pagination_offset,
        dangerous_pagination_override.

        Args:
            interval_sql: Time bucket interval for aggregation_method (computed).
        """

        # Step 1: Validate required fields are set
        if not self._project_id_int:
            raise ValueError("project_id_int must be set")
        if not self._tag_ids:
            raise ValueError("tag_ids must be set")

        # Step 2: Prep query_start and query_end for query
        query_start_str = self.query_start.astimezone(ZoneInfo("UTC")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        query_end_str = self.query_end.astimezone(ZoneInfo("UTC")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Step 3: Build aggregation_method functions for ClickHouse
        match self.aggregation_method:
            case AggregationMethod.FIRST:
                agg_functions = {
                    "value_integer": "argMin(value_integer, time)",
                    "value_bigint": "argMin(value_bigint, time)",
                    "value_real": "argMin(value_real, time)",
                    "value_double": "argMin(value_double, time)",
                    "value_boolean": "argMin(value_boolean, time)",
                    "value_text": "argMin(value_text, time)",
                }
            case AggregationMethod.AVERAGE:
                agg_functions = {
                    "value_integer": "avg(value_integer)",
                    "value_bigint": "avg(value_bigint)",
                    "value_real": "avg(value_real)",
                    "value_double": "avg(value_double)",
                    "value_boolean": "avg(toInt8(value_boolean)) > 0.5",
                    "value_text": "argMin(value_text, time)",
                }

        # Step 4: Build time bucket expression
        # If interval_sql is not None, use time_bucket expression, otherwise use time
        # as time_bucket
        if interval_sql:
            # Convert interval to ClickHouse interval format
            interval_ch = self._interval_to_clickhouse(interval_str=interval_sql)
            time_bucket_select = (
                f"toStartOfInterval(time, {interval_ch}) as time_bucket"
            )
            group_by_clause = "GROUP BY time_bucket, tag_id"
        else:
            time_bucket_select = "time as time_bucket"
            group_by_clause = "GROUP BY time, tag_id"

        # Step 5: Build pagination clause
        if self.dangerous_pagination_override:
            pagination_clause = ""
        else:
            pagination_clause = f"""
            LIMIT {self.pagination_limit}
            OFFSET {self.pagination_offset}"""

        # Step 6: Build filter clause
        tag_ids_str = ",".join(str(tid) for tid in self._tag_ids)
        filter_clause = f"tag_id IN ({tag_ids_str})"

        # Step 7: Build main query
        statement = f"""
        SELECT
            {time_bucket_select},
            tag_id,
            {agg_functions["value_integer"]} as value_integer,
            {agg_functions["value_bigint"]} as value_bigint,
            {agg_functions["value_real"]} as value_real,
            {agg_functions["value_double"]} as value_double,
            {agg_functions["value_boolean"]} as value_boolean,
            {agg_functions["value_text"]} as value_text
        FROM
            data_timeseries_1min_final
        WHERE
            project_id = {self._project_id_int}
            AND time >= '{query_start_str}'
            AND time < '{query_end_str}'
            AND {filter_clause}
        {group_by_clause}
        ORDER BY
            time_bucket, tag_id
        {pagination_clause}
        """  # noqa: S608

        return statement

    def _build_lookback_query_clickhouse(self) -> str:
        """Build ClickHouse query to get the last value before query_start for each tag.

        Uses instance attributes: _project_id_int, _tag_ids, query_start,
        max_lookback_period.
        """

        # Step 1: Validate required fields are set
        if not self._project_id_int:
            raise ValueError("project_id_int must be set")
        if not self._tag_ids:
            raise ValueError("tag_ids must be set")

        # Step 2: Calculate lookback start time, convert to UTC string format
        max_lookback_td = pd.Timedelta(self.max_lookback_period.value)
        lookback_start = self.query_start - max_lookback_td
        query_start_str = self.query_start.astimezone(ZoneInfo("UTC")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        lookback_start_str = lookback_start.astimezone(ZoneInfo("UTC")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Step 3: Build time constraint
        time_constraint = (
            f"time < '{query_start_str}' AND time >= '{lookback_start_str}'"
        )

        # Step 4: Build filter clause
        tag_ids_str = ",".join(str(tid) for tid in self._tag_ids)
        filter_clause = f"tag_id IN ({tag_ids_str})"

        # Step 5: Build main query
        statement = f"""
        SELECT
            tag_id,
            argMax(value_integer, time) as value_integer,
            argMax(value_bigint, time) as value_bigint,
            argMax(value_real, time) as value_real,
            argMax(value_double, time) as value_double,
            argMax(value_boolean, time) as value_boolean,
            argMax(value_text, time) as value_text
        FROM
            data_timeseries_1min_final
        WHERE
            project_id = {self._project_id_int}
            AND {time_constraint}
            AND {filter_clause}
        GROUP BY
            tag_id
        ORDER BY
            tag_id
        """  # noqa: S608

        return statement

    def _get_clickhouse_client(self) -> Any:
        """Get ClickHouse client for a project.

        Returns:
            ClickHouse client instance.
        """
        client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USERNAME,
            password=settings.CLICKHOUSE_PASSWORD or "",
        )

        return client

    async def _load_tags(self) -> None:
        """Load tag IDs based on filter method and values from constructor.

        Result: Sets self._tag_ids (list of tag IDs) and self._tags_lut (lookup table).
        """
        # Step 1: Initialize variables for tag/sensor type filtering
        # Result: Empty lists ready to be populated based on filter_method
        tag_ids: list[int] = []
        sensor_type_ids: list[int] = []

        # Step 2: Process filter_values based on filter_method
        # Result: Either sets _tag_ids directly or prepares query parameters
        match self.filter_method:
            # Case 1: filter_values is already a list of tag IDs
            # Result: Use filter_values directly as tag_ids, no query needed
            case FilterMethod.TAG_IDS:
                if not isinstance(self.filter_values, list):
                    raise TypeError(
                        "filter_values must be list[int] when filter_method is TAG_IDS"
                    )
                tag_ids = self.filter_values

            # Case 2: filter_values is a list of sensor type IDs
            # Result: Will query tags table to find all tags with these sensor types
            case FilterMethod.SENSOR_TYPE_IDS:
                if not isinstance(self.filter_values, list):
                    raise TypeError(
                        "filter_values must be list[int] when "
                        "filter_method is SENSOR_TYPE_IDS"
                    )
                sensor_type_ids = self.filter_values

            # Case 3: filter_values is a Polars DataFrame with tag_id column
            # Result: Extract tag_id column directly, no database query needed
            case FilterMethod.TAG_POLARS:
                if not isinstance(self.filter_values, pl.DataFrame):
                    raise TypeError(
                        "filter_values must be pl.DataFrame when "
                        "filter_method is TAG_POLARS"
                    )

                self._tag_ids = self.filter_values["tag_id"].to_list()
                self._tags_lut = self.filter_values
                return

        # Step 3: Validate that we have either tag_ids or sensor_type_ids
        # Result: Early return if neither are provided
        if not tag_ids and not sensor_type_ids:
            return

        # Step 4: Query tags table if we need to resolve tag_ids or sensor_type_ids
        # Result: Polars DataFrame with metadata (tag_id, unit_scale, unit_offset, etc.)
        # This only runs for TAG_IDS and SENSOR_TYPE_IDS cases
        tags_query = get_project_tags_v2(
            tag_ids=tag_ids,
            sensor_type_ids=sensor_type_ids,
            include_ghost_tags=True,
        )
        tags: pl.DataFrame = await tags_query.get_async(
            output_type=OutputType.POLARS,
            schema=self.project_name_short,
        )

        # Step 5: Validate that we found tags
        # Result: Early return if no tags were found
        if len(tags) == 0:
            return

        # Step 6: Extract tag IDs and store lookup table
        # Result:
        # - self._tag_ids: List of tag IDs to query
        # - self._tags_lut: Lookup table with tag metadata for unit scaling/offset
        self._tag_ids = tags["tag_id"].to_list()
        self._tags_lut = tags

    async def _load_project_details(self) -> None:
        """Load project details from database and store in instance.

        Result: Sets _time_zone, _data_cagg_interval, _project_id_int, and
        _database_provider.
        """
        # Step 1: Build SQLAlchemy query to fetch project metadata
        # Purpose: Only load the specific fields we need (performance optimization)
        # Result: Query object that will fetch time_zone, data_cagg_interval,
        #         project_id_int, and database_provider for the project
        stmt = (
            select(models.Project)
            .options(
                load_only(
                    models.Project.time_zone,
                    models.Project.data_cagg_interval,
                    models.Project.project_id_int,
                    models.Project.database_provider,
                )
            )
            .where(models.Project.name_short == self.project_name_short)
        )

        # Step 2: Execute query and get single result
        # Result: Project model instance or None if not found
        async with get_db_session_async(schema=None) as operational_db:
            result = await operational_db.execute(stmt)
            project = result.scalar_one_or_none()

        # Step 3: Validate project exists
        # Result: Raises error if project not found, otherwise continues
        if project is None:
            raise ValueError(f"Project not found: {self.project_name_short}")

        # Step 4: Store project metadata in instance attributes
        # Result: All internal state needed for query execution is now set
        # - _time_zone: Used for timezone conversion and query range cleaning
        # - _data_cagg_interval: Determines which table to query (raw vs cagg)
        # - _project_id_int: Used for ClickHouse queries (project filtering)
        # - _database_provider: Determines which query execution path to use
        self._time_zone = project.time_zone
        self._data_cagg_interval = project.data_cagg_interval
        self._project_id_int = project.project_id_int
        self._database_provider = project.database_provider

    # -- DATABASE PROVIDER NAIVE HELPERS -- #

    @staticmethod
    def _interval_to_minutes(*, interval_str: str) -> float:
        """Convert interval string to minutes for comparison.

        Parses strings like '1min', '5min', '1hour' by extracting the
        numeric portion and unit.

        Args:
            interval_str: Interval string like "5min" or "1hour".

        Returns:
            Interval duration in minutes as a float.
        """
        # Step 1: Parse interval string using regex
        # Pattern: (\d+) captures the number, (min|hour|sec) captures the unit
        # Result: Match object with groups for value and unit, or None if invalid
        match = re.match(r"(\d+)(min|hour|sec)", interval_str.lower())
        if not match:
            raise ValueError(f"Invalid interval format: {interval_str}")

        # Step 2: Extract numeric value and unit from match groups
        # Result: value is the number (e.g., 5), unit is the time unit (e.g., "min")
        value = int(match.group(1))
        unit = match.group(2)

        # Step 3: Convert to minutes based on unit
        # Result: Float representing the interval duration in minutes
        # This allows comparison of intervals regardless of unit
        if unit == "sec":
            return value / 60  # Convert seconds to minutes
        elif unit == "min":
            return value  # Already in minutes
        elif unit == "hour":
            return value * 60  # Convert hours to minutes
        else:
            raise ValueError(f"Unsupported time unit: {unit}")

    @staticmethod
    def _ensure_localized_timezone(
        *, timestamp: datetime, tzinfo: ZoneInfo
    ) -> datetime:
        """Ensure that the timestamp is localized to the given timezone.

        Args:
            timestamp: The timestamp to localize.
            tzinfo: The timezone to localize to.

        Returns:
            Timestamp in the specified timezone.
        """
        # Step 1: Check if timestamp is timezone-naive (no tzinfo)
        # Result: If naive, add timezone without changing the clock time
        #         If aware, convert to target timezone (may change clock time)
        if timestamp.tzinfo is None:
            # Naive timestamp: attach timezone without conversion
            # Result: Same clock time, now timezone-aware
            return timestamp.replace(tzinfo=tzinfo)

        # Step 2: Timezone-aware timestamp: convert to target timezone
        # Result: Clock time may change, but represents same instant in time
        return timestamp.astimezone(tzinfo)

    def _clean_query_range(self) -> None:
        """Clean the query range by ensuring that the timestamps are localized
        to the given timezone.

        Uses instance attributes: _time_zone, query_start, query_end.

        Result: Updates self.query_start and self.query_end to be timezone-aware
                in the project's timezone.
        """
        # Step 1: Create ZoneInfo object from project timezone string
        # Result: ZoneInfo object representing the project's timezone
        tzinfo = ZoneInfo(self._time_zone)

        # Step 2: Normalize query_start to project timezone
        # Result: self.query_start is now timezone-aware in project timezone
        # If it was naive, it's localized; if it had a different tz, it's converted
        self.query_start = self._ensure_localized_timezone(
            timestamp=self.query_start, tzinfo=tzinfo
        )

        # Step 3: Normalize query_end to project timezone
        # Result: self.query_end is now timezone-aware in project timezone
        self.query_end = self._ensure_localized_timezone(
            timestamp=self.query_end, tzinfo=tzinfo
        )

    @staticmethod
    def _interval_to_clickhouse(*, interval_str: str) -> str:
        """Convert interval string to ClickHouse INTERVAL format.

        Converts strings like '1min', '5min', '1hour' to ClickHouse
        INTERVAL format like 'INTERVAL 1 MINUTE', 'INTERVAL 5 MINUTE'.

        Args:
            interval_str: Interval string like "5min" or "1hour".

        Returns:
            ClickHouse INTERVAL string (e.g., "INTERVAL 5 MINUTE").
        """
        # Step 1: Parse interval string using regex
        # Result: Match object with groups for value and unit
        match = re.match(r"(\d+)(min|hour|sec)", interval_str.lower())
        if not match:
            raise ValueError(f"Invalid interval format: {interval_str}")

        # Step 2: Extract numeric value and unit
        # Result: value is the number, unit is the time unit string
        value = int(match.group(1))
        unit = match.group(2)

        # Step 3: Map unit to ClickHouse's uppercase unit format
        # Result: Dictionary mapping our unit names to ClickHouse unit names
        unit_map = {
            "sec": "SECOND",
            "min": "MINUTE",
            "hour": "HOUR",
        }

        # Step 4: Validate unit is supported
        if unit not in unit_map:
            raise ValueError(f"Unsupported time unit: {unit}")

        # Step 5: Build ClickHouse INTERVAL string
        # Result: String like "INTERVAL 5 MINUTE" for use in ClickHouse SQL
        return f"INTERVAL {value} {unit_map[unit]}"

    def _pivot_timeseries_by_tag_polars(
        self,
        *,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """
        Pivot a long-format timeseries DataFrame with multiple value_* columns
        into a wide-format DataFrame indexed by time and with tag_id columns.

        Each tag_id is expected to use only one of the value_* columns.

        Args:
            df: Timeseries data in long format
            tags: Either an executed ModelList of Tag models or a polars DataFrame with
                columns: tag_id, unit_scale, unit_offset, and optionally
                pg_data_type_id. If pg_data_type_id is provided, it will be used to
                determine the correct value column for each tag (avoiding issues with
                default values in ClickHouse). Otherwise, the function infers the value
                column from the data. Prefer Polars DataFrames for better performance.
        """

        # Step 1: Identify value columns (value_integer, value_real, etc.)
        # Result: List of column names that contain actual data values
        value_cols = [c for c in df.columns if c.startswith("value_")]
        if not value_cols:
            return df.select("time").unique().sort("time")

        # Step 2: Create lookup table for value column ordering
        # Purpose: Maintains priority order when a tag could match multiple value
        # columns
        # Result: DataFrame mapping value column names to their priority order
        order_lut = pl.DataFrame(
            {"vcol": value_cols, "vorder": list(range(len(value_cols)))}
        )

        # Step 3: Convert to lazy frame for efficient processing
        ldf = df.lazy()

        # Step 4: Unpivot value columns into long format
        # Input: Wide format with columns [time, tag_id, value_integer, value_real, ...]
        # Result: Long format with columns [time, tag_id, vcol, val]
        # Each row represents one value from one value column for one tag at one time
        long = ldf.unpivot(
            index=["time", "tag_id"],
            on=value_cols,
            variable_name="vcol",
            value_name="val",
        )

        # Step 5: Map pg_data_type_id to correct value column using lookup table
        # Purpose: Each tag has a pg_data_type_id that tells us which value_* column it
        # uses
        # Result: Mapping DataFrame: pg_data_type_id -> value column name
        # Note: Filter out unknown type IDs to avoid KeyError
        pg_type_ids = self._tags_lut["pg_data_type_id"].unique().to_list()
        known_type_ids = [
            tid for tid in pg_type_ids if tid in PG_DATA_TYPE_ID_TO_VALUE_COL
        ]
        type_to_vcol_mapping = pl.DataFrame(
            {
                "pg_data_type_id": known_type_ids,
                "vcol": [PG_DATA_TYPE_ID_TO_VALUE_COL[tid] for tid in known_type_ids],
            }
        )

        # Step 6: Join tags_lut with mapping to get tag_id -> vcol relationship
        # Result: DataFrame with columns [tag_id, vcol] showing which value column each
        # tag uses
        tags_with_vcol = (
            self._tags_lut.join(type_to_vcol_mapping, on="pg_data_type_id", how="left")
            .select(["tag_id", "vcol"])
            .filter(pl.col("vcol").is_not_null())
        )

        # Step 7: Filter to only tags where the mapped value column exists in data
        # and add ordering information for disambiguation
        # Result: DataFrame with [tag_id, vcol, vorder] for tags that have data
        # Sorted by tag_id and vorder to ensure consistent selection
        chosen_vcol = (
            tags_with_vcol.lazy()
            .filter(pl.col("vcol").is_in(value_cols))
            .join(order_lut.lazy(), on="vcol", how="left")
            .sort(["tag_id", "vorder"])
        )

        # Step 8: Filter long-format data to only include rows matching chosen_vcol
        # Result: Long-format DataFrame with only the correct value column per tag
        filtered = long.join(chosen_vcol, on=["tag_id", "vcol"], how="inner")

        # Step 9: Categorize value columns by data type
        # Purpose: Different types need different processing (numeric gets unit scaling)
        # Result: Three lists separating numeric, boolean, and text value columns
        df_schema = df.schema
        num_cols = [c for c in value_cols if df_schema[c].is_numeric()]
        bool_cols = [c for c in value_cols if isinstance(df_schema[c], Boolean)]
        txt_cols = [c for c in value_cols if isinstance(df_schema[c], String)]

        # Step 10: Process numeric values (apply unit scaling and offset)
        if num_cols:
            # Step 10a: Filter to only numeric value columns
            numeric_filtered = filtered.filter(pl.col("vcol").is_in(num_cols))

            # Step 10b: Prepare tags_lut for join
            tags_lut_lf = self._tags_lut.lazy().with_columns(
                pl.col("tag_id").cast(pl.Int64)
            )

            # Step 10c: Join with tags_lut, optionally apply unit scaling/offset,
            # pivot to wide format
            if self.apply_scale_and_offset:
                # Formula: val_adj = (val * unit_scale) + unit_offset
                numeric_wide = (
                    numeric_filtered.with_columns(pl.col("tag_id").cast(pl.Int64))
                    .join(tags_lut_lf, on="tag_id", how="left")
                    .with_columns(
                        (
                            pl.col("val").cast(pl.Float64, strict=False)
                            * pl.col("unit_scale").fill_null(1.0)
                            + pl.col("unit_offset").fill_null(0.0)
                        ).alias("val_adj")
                    )
                    .select(["time", "tag_id", "val_adj"])
                    .collect(engine="streaming")
                    .pivot(
                        index="time",
                        on="tag_id",
                        values="val_adj",
                        aggregate_function="first",
                    )
                )
            else:
                # No scaling/offset - use raw values
                numeric_wide = (
                    numeric_filtered.with_columns(
                        pl.col("val").cast(pl.Float64, strict=False).alias("val_adj")
                    )
                    .select(["time", "tag_id", "val_adj"])
                    .collect(engine="streaming")
                    .pivot(
                        index="time",
                        on="tag_id",
                        values="val_adj",
                        aggregate_function="first",
                    )
                )
        else:
            numeric_wide = None

        # Step 11: Process boolean values (no scaling, just cast and pivot)
        # Result: Wide-format DataFrame with boolean tag columns
        if bool_cols:
            bool_wide = (
                filtered.filter(pl.col("vcol").is_in(bool_cols))
                .with_columns(pl.col("val").cast(pl.Boolean).alias("val_adj"))
                .select(["time", "tag_id", "val_adj"])
                .collect(engine="streaming")
                .pivot(
                    index="time",
                    on="tag_id",
                    values="val_adj",
                    aggregate_function="first",
                )
            )
        else:
            bool_wide = None

        # Step 12: Process text values (no scaling, just cast and pivot)
        # Result: Wide-format DataFrame with text tag columns
        if txt_cols:
            text_wide = (
                filtered.filter(pl.col("vcol").is_in(txt_cols))
                .with_columns(pl.col("val").cast(pl.Utf8).alias("val_adj"))
                .select(["time", "tag_id", "val_adj"])
                .collect(engine="streaming")
                .pivot(
                    index="time",
                    on="tag_id",
                    values="val_adj",
                    aggregate_function="first",
                )
            )
        else:
            text_wide = None

        # Step 13: Combine numeric, boolean, and text DataFrames into single wide format
        # Purpose: Merge all three type-specific DataFrames on time column
        # Result: Single wide DataFrame with all tag columns (numeric, boolean, text)

        # Step 13a: Start with all unique times from original data
        # Purpose: Ensures full join aligns even if some types have missing times
        # Result: DataFrame with just time column containing all unique timestamps
        times = df.select("time").unique()

        # Step 13b: Handle edge case - empty dataframe or null time column
        # Result: Return early with just time column if no data exists
        if times.is_empty() or isinstance(times.schema["time"], pl.Null):
            return times

        # Step 13c: Normalize time format of base times DataFrame
        # Result: times DataFrame with time column in canonical format
        wide = self._canon_time(times, like=times)

        # Step 13d: Join each type-specific DataFrame (numeric, boolean, text) to base
        # Process: For each non-empty part, normalize time format then full join
        # Result: Combined DataFrame with all tag columns from all types
        for part in [numeric_wide, bool_wide, text_wide]:
            if part is None or part.is_empty():
                continue
            # Normalize time format to match base times
            part = self._canon_time(part, like=times)
            # Full join ensures all times from both DataFrames are included
            wide = (
                wide.join(part, on="time", how="full", suffix="_r").drop(
                    "time_r", strict=False
                )  # defensive in case a mismatch sneaks in
            )

        # Step 14: Sort by time and convert timezone to project timezone
        # Result: DataFrame sorted chronologically with time in project timezone
        wide = wide.sort("time").with_columns(
            pl.col("time").dt.convert_time_zone(self._time_zone)
        )

        # Step 15: Ensure all requested tags appear as columns, even if they have no
        # data
        # Purpose: Guarantees consistent output structure - all requested tags present

        # Step 15a: Get all tag IDs that were requested
        # Result: Set of all tag IDs from tags_lut
        requested_tag_ids = set(self._tag_ids)

        # Step 15b: Extract existing tag column names (convert to integers)
        # Result: Set of tag IDs that already exist as columns in wide DataFrame
        existing_tag_cols = set()
        for col in wide.columns:
            if col != "time":
                try:
                    existing_tag_cols.add(int(col))
                except (ValueError, TypeError):
                    pass

        # Step 15c: Find tags that are missing (requested but no data)
        # Result: Set of tag IDs that need null columns added
        missing_tag_ids = requested_tag_ids - existing_tag_cols

        # Step 15d: Add null columns for missing tags
        # Result: DataFrame with all requested tags as columns (some may be all null)
        if missing_tag_ids:
            for tag_id in sorted(missing_tag_ids):
                wide = wide.with_columns(pl.lit(np.nan).alias(str(tag_id)))

        return wide

    def _canon_time(self, df_part: pl.DataFrame, *, like: pl.DataFrame) -> pl.DataFrame:
        """Make df_part['time'] exactly match like['time'] in unit and timezone.

        Purpose: Normalizes time column format so DataFrames can be joined on time.
                 Ensures both DataFrames have same time unit (microseconds/nanoseconds)
                 and timezone (aware/naive, and which timezone if aware).

        Args:
            df_part: DataFrame whose time column will be normalized.
            like: Reference DataFrame providing the desired time dtype.

        Returns:
            DataFrame with time column matching like's time column format.
        """
        # Step 1: Get reference time column schema
        # Result: Polars datatype object describing the desired time format
        ref_dt = like.schema["time"]

        # Step 2: Handle edge case - reference time column is Null
        # Result: Return df_part unchanged if reference has no time data
        if isinstance(ref_dt, pl.Null):
            return df_part

        # Step 3: Validate reference time column is Datetime type
        if not isinstance(ref_dt, pl.Datetime):
            raise TypeError(f"Expected Datetime, got {type(ref_dt)}")

        # Step 4: Extract reference time unit and timezone
        # Result: ref_unit is "us" or "ns", ref_tz is timezone string or None
        ref_unit = ref_dt.time_unit  # "us" or "ns"
        ref_tz = ref_dt.time_zone  # e.g. "UTC", "America/Chicago", or None

        # Step 5: Get current time column schema
        # Result: Polars datatype object describing df_part's current time format
        cur_dt = df_part.schema["time"]

        # Step 6: Handle edge case - current time column is Null
        # Result: Return df_part unchanged if it has no time data
        if isinstance(cur_dt, pl.Null):
            return df_part

        # Step 7: Validate current time column is Datetime type
        if not isinstance(cur_dt, pl.Datetime):
            raise TypeError(f"Expected Datetime, got {type(cur_dt)}")
        cur_tz = cur_dt.time_zone

        # Step 8: Normalize time unit to match reference
        # Result: DataFrame with time column in same unit (us/ns) as reference
        out = df_part.with_columns(pl.col("time").dt.cast_time_unit(ref_unit))

        # Step 9: Align timezone to match reference
        # Result: DataFrame with time column in same timezone as reference
        if ref_tz is None:
            # Case 9a: Reference wants timezone-naive output
            if cur_tz is not None:
                # Current is aware: convert to UTC then drop timezone info
                # Result: Clock time preserved, timezone info removed
                out = out.with_columns(
                    pl.col("time")
                    .dt.convert_time_zone("UTC")
                    .dt.replace_time_zone(None)
                )
            # else already naive - no change needed
        else:
            # Case 9b: Reference wants timezone-aware output with specific timezone
            if cur_tz is None:
                # Current is naive: attach timezone without changing clock time
                # Result: Same clock time, now timezone-aware
                out = out.with_columns(pl.col("time").dt.replace_time_zone(ref_tz))
            elif cur_tz != ref_tz:
                # Current has different timezone: convert to reference timezone
                # Result: Clock time may change, but represents same instant
                out = out.with_columns(pl.col("time").dt.convert_time_zone(ref_tz))

        # Step 10: Return normalized DataFrame
        # Result: DataFrame with time column matching reference format exactly
        return out


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
    """Fetch timeseries data using the legacy SQL builder.

    Args:
        project_db: Sync session for the project schema.
        project_name_short: Project schema name to query.
        tag_ids: Tag ids to include.
        start: Inclusive start time for the query.
        end: Exclusive end time for the query.
        interval: Aggregation interval string.
        cagg_interval: Optional cagg interval string to query.
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
