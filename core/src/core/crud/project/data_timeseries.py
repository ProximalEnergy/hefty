import re
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, cast, overload
from zoneinfo import ZoneInfo

import clickhouse_connect
import pandas as pd
import polars as pl
from polars.datatypes import Boolean, String
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    Table,
    Text,
    bindparam,
    select,
    text,
)
from sqlalchemy import Boolean as sa_Boolean
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import Session

from core import settings
from core.crud.project.query_metadata_cache import (
    get_project_query_metadata_cached,
)
from core.crud.project.tags import get_project_tags_v2
from core.db_query import DbQuery, OutputType
from core.enumerations import (
    AggregationMethod,
    ProjectDatabaseProvider,
    TimeInterval,
    TimeOffset,
)

try:
    from fastapi import HTTPException

    FASTAPI_INSTALLED = True
except ImportError:
    FASTAPI_INSTALLED = False

warnings.filterwarnings(
    "ignore", message="Did not recognize type 'ltree'", category=sa_exc.SAWarning
)


class FilterMethod(Enum):
    """Tag query filter methods."""

    TAG_IDS = "tag_ids"
    TAG_POLARS = "tag_polars"
    TAGS_PANDAS = "tags_pandas"
    SENSOR_TYPE_IDS = "sensor_type_ids"


# Mapping from pg_data_type_id to value column name
PG_DATA_TYPE_ID_TO_VALUE_COL: dict[int, str] = {
    1: "value_integer",
    2: "value_bigint",
    3: "value_real",
    4: "value_double",
    5: "value_boolean",
    6: "value_text",
}

# Mapping from value column name to Polars data type
VALUE_COL_TO_DTYPE: dict[str, pl.DataType] = {
    "value_integer": pl.Float64(),
    "value_bigint": pl.Float64(),
    "value_real": pl.Float64(),
    "value_double": pl.Float64(),
    "value_boolean": pl.Boolean(),
    "value_text": pl.Utf8(),
}


@dataclass(slots=True, init=False)
class DataTimeseries:
    # Required fields, must be provided in constructor
    project_name_short: str
    filter_method: FilterMethod
    filter_values: list[int] | pd.DataFrame | pl.DataFrame
    query_start: datetime
    query_end: datetime
    project_db: Session

    # Optional fields (with defaults)
    max_lookback_period: TimeOffset = TimeOffset.FIVE_MINUTES
    freq: TimeInterval = TimeInterval.FIVE_MINUTES
    aggregation_method: AggregationMethod = AggregationMethod.FIRST
    pagination_limit: int = 1_000_000
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
    _tag_dtype_by_id: dict[int, pl.DataType] = field(default_factory=dict)
    _prepared: bool = False

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

    @overload
    def __init__(
        self,
        *,
        project_name_short: str,
        filter_method: Literal[FilterMethod.TAGS_PANDAS],
        filter_values: pd.DataFrame,
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
        filter_values: list[int] | pd.DataFrame | pl.DataFrame,
        query_start: datetime,
        query_end: datetime,
        project_db: Session,
        max_lookback_period: TimeOffset = TimeOffset.FIVE_MINUTES,
        freq: TimeInterval = TimeInterval.FIVE_MINUTES,
        aggregation_method: AggregationMethod = AggregationMethod.FIRST,
        pagination_limit: int = 1_000_000,
        pagination_offset: int = 0,
        dangerous_pagination_override: bool = False,
        ffill_limit: int | None = None,
        ensure_full_range: bool = True,
        apply_scale_and_offset: bool = True,
    ) -> None:
        """Initialize a timeseries query configuration.

        Args:
            project_name_short: Project short name used for metadata resolution.
            filter_method: Strategy used to resolve tag filters.
            filter_values: Tag IDs or lookup table matching `filter_method`.
            query_start: Inclusive query start timestamp.
            query_end: Exclusive query end timestamp.
            project_db: Database session for project metadata and queries.
            max_lookback_period: Optional lookback window for backfilling.
            freq: Output aggregation interval.
            aggregation_method: Aggregation to apply per interval.
            pagination_limit: Maximum rows to fetch per page.
            pagination_offset: Offset applied to paginated queries.
            dangerous_pagination_override: Allow pagination without guardrails.
            ffill_limit: Max periods to forward fill when backfilling.
            ensure_full_range: Backfill missing timestamps across the range.
            apply_scale_and_offset: Apply tag scale and offset metadata.
        """
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
        self._prepared = False

    async def get(self) -> "DataTimeseries":
        """Execute the timeseries query using constructor parameters.

        Returns:
            Self with df, and page_limit_reached populated.
        """
        # Prepare metadata and resolve tags
        if not await self._prepare():
            return self

        # Build provider context based on database provider
        context = self._build_provider_context()

        # Fetch data from provider
        lookback_df = await self._fetch_provider_lookback(context=context)
        df = await self._fetch_provider_page(context=context)

        # Post process data
        df, page_limit_reached = await self._post_process_data_timeseries(
            df=df,
            lookback_df=lookback_df,
        )

        # Set public fields
        self.df = df
        self.page_limit_reached = page_limit_reached

        return self

    async def get_all(self) -> "DataTimeseries":
        """Execute paginated queries until the full range is retrieved.

        Returns:
            Self with df populated across all pages.
        """
        # Prepare metadata and resolve tags
        if not await self._prepare():
            return self

        # Cache initial values
        initial_offset = self.pagination_offset
        initial_ffill_limit = self.ffill_limit

        # Initialize lookback and pages list
        lookback_df = pl.DataFrame()
        pages: list[pl.DataFrame] = []

        try:
            # Set ffill_limit to 0 to avoid premature forward filling
            self.ffill_limit = 0

            # Build provider context based on database provider
            context = self._build_provider_context()

            # Fetch lookback data from provider
            lookback_df = await self._fetch_provider_lookback(context=context)

            MAX_PAGE_GUARD = 100
            page_guard = 0

            # Keep fetching pages until the pagination limit is reached
            while True:
                # Fetch page data from provider
                df = await self._fetch_provider_page(context=context)

                # Add page to pages list
                pages.append(df)

                # If page height is less than the pagination limit, break
                if df.height < self.pagination_limit:
                    break

                # Increment pagination offset
                self.pagination_offset += self.pagination_limit

                # Increment page guard
                page_guard += 1

                # If page guard is greater than the max page guard, break
                if page_guard > MAX_PAGE_GUARD:
                    warnings.warn("Max page guard reached, returning partial data")
                    break
        finally:
            # Restore initial values
            self.pagination_offset = initial_offset
            self.ffill_limit = initial_ffill_limit

        # Combine pages into a single DataFrame
        combined = pl.concat(pages, how="vertical") if pages else pl.DataFrame()

        # Post process data
        df, _ = await self._post_process_data_timeseries(
            df=combined,
            lookback_df=lookback_df,
            check_pagination_limit=False,
        )

        # Set public fields
        self.df = df
        self.page_limit_reached = False

        return self

    def raise_on_empty_df(self):
        if not FASTAPI_INSTALLED:
            raise RuntimeError("fastapi not installed")
        if self.df.is_empty():
            raise HTTPException(status_code=400, detail="No data found")

        time_col = self._get_time_column(df=self.df)
        value_cols = [col for col in self.df.columns if col != time_col]
        if not value_cols:
            raise HTTPException(status_code=400, detail="No data found")

        all_null = self.df.select(
            [pl.col(col).is_null().all().alias(col) for col in value_cols]
        ).row(0)
        if all(all_null):
            raise HTTPException(status_code=400, detail="No data found")

    async def _prepare(self) -> bool:
        """Load project details, normalize query range, and resolve tags.

        Returns:
            True when tags are available to query, otherwise False.
        """
        # If already prepared, return True if tags are available
        if self._prepared:
            return len(self._tag_ids) > 0

        # Fetch project details
        await self._load_project_details()

        # Clean query range
        self._clean_query_range()

        # Fetch tags
        await self._load_tags()

        # If no tags are found, warn and return empty DataFrame
        if not self._tag_ids:
            warnings.warn("No tag_ids found, returning empty DataFrame")

            # If ensure_full_range, build full time range
            if self.ensure_full_range:
                self.df = self._build_full_range_frame(time_col="time")

            # Otherwise, build empty time range
            else:
                self.df = self._empty_time_frame(time_col="time")

            # Set attributes
            self.page_limit_reached = False
            self._prepared = True

            return False

        # Set attributes
        self._prepared = True

        return True

    @dataclass(frozen=True, slots=True)
    class _ProviderContext:
        """Provider context for lookback/page fetches."""

        provider: ProjectDatabaseProvider
        table_name: str | None
        interval_sql: TimeInterval | None
        client: Any | None

    def _build_provider_context(self) -> _ProviderContext:
        """Build provider-specific context for lookback/page fetches."""
        if self._database_provider is None:
            raise ValueError("database_provider must be set")

        match self._database_provider:
            case ProjectDatabaseProvider.TIMESCALE:
                table, interval_sql = self._build_table_and_interval_sql_timescale()
                return self._ProviderContext(
                    provider=self._database_provider,
                    table_name=table,
                    interval_sql=interval_sql,
                    client=None,
                )
            case ProjectDatabaseProvider.CLICKHOUSE:
                if not self._project_id_int:
                    raise ValueError("project_id_int must be set")
                if not self._time_zone:
                    raise ValueError("time_zone must be set")
                interval_sql = self._build_interval_sql_clickhouse()
                return self._ProviderContext(
                    provider=self._database_provider,
                    table_name=None,
                    interval_sql=interval_sql,
                    client=self._get_clickhouse_client(),
                )

    async def _fetch_provider_lookback(
        self,
        *,
        context: _ProviderContext,
    ) -> pl.DataFrame:
        """Fetch lookback data for the configured provider.

        Args:
            context: Provider-specific query context.
        """
        match context.provider:
            case ProjectDatabaseProvider.TIMESCALE:
                if context.table_name is None:
                    raise ValueError("table_name must be set for Timescale")
                return await self._fetch_timescale_lookback(
                    table_name=context.table_name,
                )
            case ProjectDatabaseProvider.CLICKHOUSE:
                if context.client is None:
                    raise ValueError("client must be set for ClickHouse")
                return self._fetch_clickhouse_lookback(client=context.client)

    async def _fetch_provider_page(
        self,
        *,
        context: _ProviderContext,
    ) -> pl.DataFrame:
        """Fetch a single page for the configured provider.

        Args:
            context: Provider-specific query context.
        """
        match context.provider:
            case ProjectDatabaseProvider.TIMESCALE:
                if context.table_name is None:
                    raise ValueError("table_name must be set for Timescale")
                return await self._fetch_timescale_page(
                    table_name=context.table_name,
                    interval_sql=context.interval_sql,
                )
            case ProjectDatabaseProvider.CLICKHOUSE:
                if context.client is None:
                    raise ValueError("client must be set for ClickHouse")
                return self._fetch_clickhouse_page(
                    client=context.client,
                    interval_sql=context.interval_sql,
                )

    async def _fetch_timescale_lookback(
        self,
        *,
        table_name: str,
    ) -> pl.DataFrame:
        """Fetch lookback data for Timescale.

        Args:
            table_name: Timescale table name to query.
        """
        db_query = self._build_lookback_query_timescale(
            table_name=table_name,
        )
        return await db_query.get_async(
            output_type=OutputType.POLARS,
            schema=self.project_name_short,
        )

    async def _fetch_timescale_page(
        self,
        *,
        table_name: str,
        interval_sql: TimeInterval | None,
    ) -> pl.DataFrame:
        """Fetch a single Timescale page (raw long format).

        Args:
            table_name: Timescale table name to query.
            interval_sql: Optional aggregation interval.
        """
        db_query = self._build_data_timeseries_query_timescale(
            table_name=table_name,
            interval_sql=interval_sql,
        )
        return await db_query.get_async(
            output_type=OutputType.POLARS,
            schema=self.project_name_short,
        )

    def _fetch_clickhouse_lookback(self, *, client: Any) -> pl.DataFrame:
        """Fetch lookback data for ClickHouse.

        Args:
            client: ClickHouse client instance.
        """
        lookback_query = self._build_lookback_query_clickhouse()
        result = client.query_df_arrow(
            lookback_query,
            dataframe_library="polars",
        )
        return cast(pl.DataFrame, result)

    def _fetch_clickhouse_page(
        self,
        *,
        client: Any,
        interval_sql: TimeInterval | None,
    ) -> pl.DataFrame:
        """Fetch a single ClickHouse page (raw long format).

        Args:
            client: ClickHouse client instance.
            interval_sql: Optional aggregation interval.
        """
        query = self._build_data_timeseries_query_clickhouse(
            interval_sql=interval_sql,
        )
        df = cast(
            pl.DataFrame,
            client.query_df_arrow(
                query,
                dataframe_library="polars",
            ),
        )
        df = df.rename({"time_bucket": "time"})
        if not isinstance(df["time"].dtype, pl.Datetime):
            df = df.with_columns(
                pl.from_epoch(pl.col("time"), time_unit="s").alias("time")
            )
        return df

    async def _post_process_data_timeseries(
        self,
        *,
        df: pl.DataFrame,
        lookback_df: pl.DataFrame,
        check_pagination_limit: bool = True,
    ) -> tuple[pl.DataFrame, bool]:
        """Post-process timeseries data: pivot, apply lookback, forward fill,
                and ensure full range.

        Uses instance attributes for configuration: project_db, _time_zone,
        ffill_limit, ensure_full_range, query_start, query_end, freq,
        pagination_limit, dangerous_pagination_override.

        Args:
            df: Raw timeseries data from the main query.
            lookback_df: Last-known values prior to query_start.
            check_pagination_limit: Whether to compute page_limit_reached.
        """
        # Step 1: Check if pagination limit was reached
        # If result size equals limit and override is not enabled, we hit the limit,
        # meaning there may be more data available
        if (
            check_pagination_limit
            and df.height == self.pagination_limit
            and not self.dangerous_pagination_override
        ):
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
        time_col = self._get_time_column(df=df)
        df = self._ensure_time_column(df=df, time_col=time_col)

        # Step 4: Ensure full time range coverage if requested
        # Result: DataFrame with rows for every timestamp in [query_start, query_end)
        if self.ensure_full_range:
            # Step 4a: Build complete time range DataFrame
            full_range_df = self._build_full_range_frame(time_col=time_col)

            # Step 4b: Normalize df time column for join compatibility
            df = self._normalize_time_column(df=df, time_col=time_col)

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

        df = self._normalize_time_column(df=df, time_col=time_col)
        df = self._apply_forward_fill(df=df, time_col=time_col)

        df = self._ensure_tag_columns(df=df, time_col=time_col)
        return df, page_limit_reached

    def _apply_forward_fill(
        self,
        *,
        df: pl.DataFrame,
        time_col: str,
    ) -> pl.DataFrame:
        """Forward fill null values up to current time.

        Args:
            df: DataFrame to forward fill.
            time_col: Name of the time column.
        """
        if self.ffill_limit == 0:
            return df

        # Get current time in project timezone for comparison
        now = datetime.now(ZoneInfo(self._time_zone))

        # Identify data columns (exclude time columns)
        data_cols = [c for c in df.columns if c not in [time_col, "time"]]

        # Apply forward fill with time-based condition
        return df.with_columns(
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
    ) -> DbQuery:
        """Build query to get the last value before query_start for each tag.

        Uses instance attributes: project_name_short, query_start,
        max_lookback_period, _tag_ids.

        Args:
            table_name: Table name to query.
        """
        # Step 1: Create SQLAlchemy Table object using schema translation
        # Result: Table object representing the timeseries table in project schema
        metadata = MetaData(schema="project")
        table = Table(
            table_name,
            metadata,
            Column("time", DateTime(timezone=True)),
            Column("tag_id", Integer),
            Column("value_integer", Integer),
            Column("value_bigint", BigInteger),
            Column("value_real", Float),
            Column("value_double", Float),
            Column("value_boolean", sa_Boolean),
            Column("value_text", Text),
            schema="project",
        )

        # Step 2: Calculate lookback time window
        # Defines the time window to search for prior values
        max_lookback_td = pd.Timedelta(self.max_lookback_period.value)
        lookback_start = self.query_start - max_lookback_td

        # Step 3: Build time constraint SQL and bind parameters
        bind_params = {
            "query_start": self.query_start,
            "lookback_start": lookback_start,
            "filter_ids": tuple(self._tag_ids),
        }

        # Step 4: Build SQL query using DISTINCT ON for efficiency
        # Purpose: Get the most recent value per tag within the lookback window
        statement = (
            select(
                table.c.tag_id,
                table.c.value_integer,
                table.c.value_bigint,
                table.c.value_real,
                table.c.value_double,
                table.c.value_boolean,
                table.c.value_text,
            )
            .distinct(table.c.tag_id)
            .where(
                table.c.time < bindparam("query_start"),
                table.c.time >= bindparam("lookback_start"),
                table.c.tag_id.in_(bindparam("filter_ids", expanding=True)),
            )
            .order_by(table.c.tag_id, table.c.time.desc())
        )

        # Step 5: Create DbQuery with bound Select
        # Result: Executable DbQuery object ready for execution
        return DbQuery(query=statement.params(**bind_params))

    def _build_data_timeseries_query_timescale(
        self,
        *,
        table_name: str,
        interval_sql: TimeInterval | None,
    ) -> DbQuery:
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
        query_start_ts = self.query_start
        query_end_ts = self.query_end

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
            "query_start": query_start_ts,
            "query_end": query_end_ts,
            "filter_ids": tuple(self._tag_ids),
        }
        # Add pagination params if not overridden
        if not self.dangerous_pagination_override:
            bind_params["pagination_limit"] = self.pagination_limit
            bind_params["pagination_offset"] = self.pagination_offset
        # Add interval param if time bucketing is used
        if interval_sql:
            bind_params["interval"] = pd.Timedelta(interval_sql.value).to_pytimedelta()

        # Step 9: Create DbQuery with bound TextClause
        # Result: Executable DbQuery object ready for execution
        return DbQuery(
            query=text(statement).bindparams(
                bindparam("filter_ids", expanding=True),
                **bind_params,
            )
        )

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
                warnings.warn(
                    "FilterMethod.TAG_IDS leads to an additional database query. "
                    "Consider using FilterMethod.TAG_POLARS instead.",
                    stacklevel=5,
                )
                if not isinstance(self.filter_values, list):
                    raise TypeError(
                        "filter_values must be list[int] when filter_method is TAG_IDS"
                    )
                tag_ids = self.filter_values

            # Case 2: filter_values is a list of sensor type IDs
            # Result: Will query tags table to find all tags with these sensor types
            case FilterMethod.SENSOR_TYPE_IDS:
                warnings.warn(
                    "FilterMethod.TAG_IDS leads to an additional database query. "
                    "Consider using FilterMethod.TAG_POLARS instead.",
                    stacklevel=5,
                )
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
                self._tag_dtype_by_id = {}
                return

            # Case 4: filter_values is a Pandas DataFrame with tag_id column
            # Result: Convert to Polars, extract tag_id column directly
            case FilterMethod.TAGS_PANDAS:
                if not isinstance(self.filter_values, pd.DataFrame):
                    raise TypeError(
                        "filter_values must be pd.DataFrame when "
                        "filter_method is TAGS_PANDAS"
                    )

                tags_polars = pl.from_pandas(self.filter_values)
                self._tag_ids = tags_polars["tag_id"].cast(pl.Int64).to_list()
                self._tags_lut = tags_polars
                self._tag_dtype_by_id = {}
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
        self._tag_dtype_by_id = {}

    async def _load_project_details(self) -> None:
        """Load project details from database and store in instance.

        Result: Sets _time_zone, _data_cagg_interval, _project_id_int, and
        _database_provider.
        """
        project = await get_project_query_metadata_cached(
            project_name_short=self.project_name_short
        )
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
        """

        # Step 1: Identify value columns (value_integer, value_real, etc.)
        # Result: List of column names that contain actual data values
        value_cols = [c for c in df.columns if c.startswith("value_")]
        if not value_cols:
            time_col = self._get_time_column(df=df)
            if time_col in df.columns:
                times = df.select(time_col).unique().sort(time_col)
            else:
                times = self._empty_time_frame(time_col=time_col)
            return self._ensure_tag_columns(df=times, time_col=time_col)

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
            return self._ensure_tag_columns(df=times, time_col="time")

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

        return self._ensure_tag_columns(df=wide, time_col="time")

    def _ensure_tag_columns(
        self,
        *,
        df: pl.DataFrame,
        time_col: str,
    ) -> pl.DataFrame:
        """Ensure all requested tag_ids exist as columns.

        Args:
            df: DataFrame to update.
            time_col: Name of the time column to exclude from tag checks.
        """
        requested_tag_ids = set(self._tag_ids)
        tag_dtype_by_id = self._get_tag_dtype_by_id()

        existing_tag_cols = set()
        for col in df.columns:
            if col == time_col:
                continue
            try:
                tag_id = int(col)
                existing_tag_cols.add(tag_id)
            except (ValueError, TypeError):
                continue
            col_dtype = df.schema[col]
            if isinstance(col_dtype, pl.Null):
                dtype = tag_dtype_by_id.get(tag_id)
                if dtype is not None:
                    df = df.with_columns(pl.col(col).cast(dtype).alias(col))

        missing_tag_ids = requested_tag_ids - existing_tag_cols
        for tag_id in sorted(missing_tag_ids):
            dtype = tag_dtype_by_id.get(tag_id)
            if dtype is None:
                df = df.with_columns(pl.lit(None).alias(str(tag_id)))
            else:
                df = df.with_columns(pl.lit(None).cast(dtype).alias(str(tag_id)))
        return df

    @staticmethod
    def _get_time_column(*, df: pl.DataFrame) -> str:
        """Get the time column name from a DataFrame.

        Args:
            df: DataFrame to inspect.
        """
        if "time" in df.columns:
            return "time"
        if "time_bucket" in df.columns:
            return "time_bucket"
        return "time"

    def _ensure_time_column(self, *, df: pl.DataFrame, time_col: str) -> pl.DataFrame:
        """Ensure the DataFrame contains a normalized time column.

        Args:
            df: DataFrame to normalize.
            time_col: Expected time column name.

        Returns:
            DataFrame with a timezone-normalized time column.
        """
        if time_col not in df.columns:
            df = self._empty_time_frame(time_col=time_col)
        return self._normalize_time_column(df=df, time_col=time_col)

    def _normalize_time_column(
        self,
        *,
        df: pl.DataFrame,
        time_col: str,
    ) -> pl.DataFrame:
        """Normalize the time column to microseconds in the project timezone.

        Args:
            df: DataFrame to normalize.
            time_col: Name of the time column to inspect.

        Returns:
            DataFrame with the normalized time column.
        """
        time_dtype = df.schema[time_col]
        if isinstance(time_dtype, pl.Null):
            return df.with_columns(
                pl.lit(None)
                .cast(pl.Datetime(time_unit="us", time_zone=self._time_zone))
                .alias(time_col)
            )
        if not isinstance(time_dtype, pl.Datetime):
            return df
        if time_dtype.time_unit != "us":
            df = df.with_columns(pl.col(time_col).dt.cast_time_unit("us"))
        if time_dtype.time_zone is None:
            return df.with_columns(
                pl.col(time_col).dt.replace_time_zone(self._time_zone)
            )
        if time_dtype.time_zone != self._time_zone:
            return df.with_columns(
                pl.col(time_col).dt.convert_time_zone(self._time_zone)
            )
        return df

    def _build_full_range_frame(self, *, time_col: str) -> pl.DataFrame:
        """Build a full time range DataFrame for the current query window.

        Args:
            time_col: Column name to use for generated timestamps.

        Returns:
            DataFrame containing the complete expected time range.
        """
        interval_td = pd.Timedelta(self.freq.value).to_pytimedelta()
        full_range = pl.datetime_range(
            start=self.query_start,
            end=self.query_end,
            interval=interval_td,
            closed="left",
            eager=True,
        )
        full_range_df = pl.DataFrame({time_col: full_range})
        return self._normalize_time_column(
            df=full_range_df,
            time_col=time_col,
        )

    def _empty_time_frame(self, *, time_col: str) -> pl.DataFrame:
        """Build an empty time-only DataFrame with the project timezone.

        Args:
            time_col: Name for the time column.
        """
        time_dtype = pl.Datetime(time_unit="us", time_zone=self._time_zone)
        return pl.DataFrame({time_col: pl.Series(time_col, [], dtype=time_dtype)})

    def _get_tag_dtype_by_id(self) -> dict[int, pl.DataType]:
        if self._tag_dtype_by_id:
            return self._tag_dtype_by_id
        if "pg_data_type_id" not in self._tags_lut.columns:
            return {}
        tag_dtype_by_id: dict[int, pl.DataType] = {}
        for row in self._tags_lut.select(["tag_id", "pg_data_type_id"]).to_dicts():
            value_col = PG_DATA_TYPE_ID_TO_VALUE_COL.get(row["pg_data_type_id"])
            if value_col is None:
                continue
            dtype = VALUE_COL_TO_DTYPE.get(value_col)
            if dtype is None:
                continue
            tag_dtype_by_id[int(row["tag_id"])] = dtype
        self._tag_dtype_by_id = tag_dtype_by_id
        return tag_dtype_by_id

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
