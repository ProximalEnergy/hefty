import warnings

import pandas as pd
from sqlalchemy import MetaData, Table, TextClause, text
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import Session

from core import models
from core.enumerations import AggregationType
from core.model_list import ModelList

warnings.filterwarnings(
    "ignore", message="Did not recognize type 'ltree'", category=sa_exc.SAWarning
)


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
    if cagg_interval:
        table_name = f"data_timeseries_{cagg_interval}"
    else:
        table_name = "data_timeseries"

    metadata = MetaData(schema=project_name_short)
    table = Table(
        table_name, metadata, schema=project_name_short, autoload_with=project_db.bind
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


def get_project_data_timeseries_v2(
    *,
    project_name_short: str,
    tag_ids: list[int] | None = None,
    sensor_type_ids: list[int] | None = None,
    start: pd.Timestamp,
    end: pd.Timestamp,
    interval: str,
    cagg_interval: str | None = None,
    aggregation: AggregationType = AggregationType.LAST,
    return_query: bool = True,
) -> ModelList[models.DataTimeseries]:
    """Get project data timeseries with configurable aggregation (v2).

    Args:
        project_name_short: Short name of the project
        tag_ids: List of tag IDs to query (mutually exclusive with sensor_type_ids)
        sensor_type_ids: List of sensor type IDs to query (mutually exclusive
            with tag_ids)
        start: Start timestamp
        end: End timestamp
        interval: Time interval for bucketing (e.g., "1 hour", "30 minutes")
        cagg_interval: Optional continuous aggregation interval
        aggregation: Type of aggregation to use (LAST or AVERAGE)
        return_query: Whether to return the query object

    Returns:
        ModelList of DataTimeseries objects

    Raises:
        ValueError: If both tag_ids and sensor_type_ids are provided or if
            neither is provided

    Examples:
        Query by specific tag IDs:
        >>> result = get_project_data_timeseries_v2(
        ...     project_name_short="my_project",
        ...     tag_ids=[1, 2, 3],
        ...     start=pd.Timestamp("2025-01-01"),
        ...     end=pd.Timestamp("2025-01-02"),
        ...     interval="1 hour"
        ... )

        Query by sensor type IDs:
        >>> result = get_project_data_timeseries_v2(
        ...     project_name_short="my_project",
        ...     sensor_type_ids=[10, 20],
        ...     start=pd.Timestamp("2025-01-01"),
        ...     end=pd.Timestamp("2025-01-02"),
        ...     interval="30 minutes",
        ...     aggregation=AggregationType.AVERAGE
        ... )
    """

    # Validate input parameters
    if tag_ids is not None and sensor_type_ids is not None:
        raise ValueError("Cannot specify both tag_ids and sensor_type_ids")
    if tag_ids is None and sensor_type_ids is None:
        raise ValueError("Must specify either tag_ids or sensor_type_ids")

    # Build schema and table in a sql-injection safe manner
    if cagg_interval:
        table_name = f"data_timeseries_{cagg_interval}"
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

    # S608:  SQL Injection avoided by using Table from sqlalchemy
    # Build the query based on whether we're filtering by tag_ids or sensor_type_ids
    if tag_ids is not None:
        # Direct tag_id filtering (original behavior)
        statement = f"""
        SELECT
            time_bucket(:interval, dt.time) + interval :interval as time_bucket,
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
            dt.time >= :start and dt.time < :end and dt.tag_id IN :filter_ids
        GROUP BY
            time_bucket, dt.tag_id
        ORDER BY
            time_bucket, dt.tag_id;
        """  # noqa: S608

        bind_params = {
            "interval": interval,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "filter_ids": tuple(tag_ids) if tag_ids is not None else (),
        }
    else:
        # sensor_type_ids filtering with JOIN
        statement = f"""
        SELECT
            time_bucket(:interval, dt.time) + interval :interval as time_bucket,
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
            dt.time >= :start and dt.time < :end and t.sensor_type_id IN :filter_ids
        GROUP BY
            time_bucket, dt.tag_id
        ORDER BY
            time_bucket, dt.tag_id;
        """  # noqa: S608

        bind_params = {
            "interval": interval,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "filter_ids": tuple(sensor_type_ids) if sensor_type_ids is not None else (),
        }

    query: TextClause = text(statement).bindparams(**bind_params)

    return ModelList(query=query, return_query=return_query)


# if __name__ == "__main__":
#     import asyncio

#     from core.dependencies import with_db, with_db_async

#     async def compare_v1_and_v2():
#         # Test parameters
#         project_name_short = "north_star"
#         tag_ids = [1, 2]  # Test with multiple tag IDs
#         start = pd.Timestamp("2025-09-22 00:00:00")
#         end = pd.Timestamp("2025-09-23 00:00:00")
#         interval = "1 hour"
#         cagg_interval = None

#         print(f"Comparing v1 and v2 functions with:")
#         print(f"  Project: {project_name_short}")
#         print(f"  Tag IDs: {tag_ids}")
#         print(f"  Start: {start}")
#         print(f"  End: {end}")
#         print(f"  Interval: {interval}")
#         print(f"  CAGG Interval: {cagg_interval}")
#         print("=" * 60)

#         # Test v1 (synchronous)
#         print("\n📊 Testing v1 (synchronous)...")
#         with with_db(schema=project_name_short) as project_db:
#             v1_result = get_project_data_timeseries(
#                 project_db=project_db,
#                 project_name_short=project_name_short,
#                 tag_ids=tag_ids,
#                 start=start,
#                 end=end,
#                 interval=interval,
#                 cagg_interval=cagg_interval,
#             )

#             # Convert v1 result to pandas DataFrame and examine structure
#             v1_pandas_df = v1_result.pandas_dataframe()
#             print(f"V1 pandas DataFrame info:")
#             print(f"  Shape: {v1_pandas_df.shape}")
#             print(f"  Columns: {list(v1_pandas_df.columns)}")
#             print(f"  Dtypes: {v1_pandas_df.dtypes.to_dict()}")
#             print("V1 first 3 rows (pandas):")
#             print(v1_pandas_df.head(3))

#             # Convert to dictionary format for comparison
#             v1_data = []
#             for _, row in v1_pandas_df.iterrows():
#                 v1_data.append(row.to_dict())
#             print(f"V1 converted to {len(v1_data)} records")

#         # Test v2 (asynchronous)
#         print("\n📊 Testing v2 (asynchronous)...")
#         v2_result = get_project_data_timeseries_v2(
#             project_name_short=project_name_short,
#             tag_ids=tag_ids,
#             start=start,
#             end=end,
#             interval=interval,
#             cagg_interval=cagg_interval,
#             return_query=True,
#         )

#         v2_df = await v2_result.polars_dataframe_async()
#         print(f"V2 Polars DataFrame info:")
#         print(f"  Shape: {v2_df.shape}")
#         print(f"  Columns: {list(v2_df.columns)}")
#         print(f"  Dtypes: {v2_df.dtypes}")
#         print("V2 first 3 rows (polars):")
#         print(v2_df.head(3))

#         # Convert to dictionary format for comparison
#         v2_data = v2_df.to_dicts()
#         print(f"V2 converted to {len(v2_data)} records")

#         # Compare results
#         print("\n🔍 Comparing results...")

#         # Check record counts
#         if len(v1_data) == len(v2_data):
#             print(f"✅ Record counts match: {len(v1_data)}")
#         else:
#             print(f"❌ Record counts differ: V1={len(v1_data)}, V2={len(v2_data)}")
#             return

#         if len(v1_data) == 0:
#             print("⚠️  No data returned from either query")
#             return

#         # Both V1 and V2 should now use 'time' column after our ModelList fix
#         # No normalization needed anymore

#         # Sort both datasets by time_bucket and tag_id for consistent comparison
#         def sort_key(record):
#             return (record.get("time_bucket"), record.get("tag_id"))

#         v1_sorted = sorted(v1_data, key=lambda r: (r.get("time"), r.get("tag_id")))
#         v2_sorted = sorted(v2_data, key=lambda r: (r.get("time"), r.get("tag_id")))

#         # Compare data values
#         try:
#             mismatches = 0
#             data_mismatches = 0

#             for i in range(min(len(v1_sorted), len(v2_sorted))):
#                 v1_record = v1_sorted[i]
#                 v2_record = v2_sorted[i]

#                 # Compare each field (excluding time fields for now)
#                 record_differs = False
#                 time_differs = False

#                 for key in v1_record.keys():
#                     if key == "time":
#                         # Compare time values (convert both to strings for comparison)
#                         v1_time_str = str(v1_record[key])
#                         v2_time_str = str(v2_record[key])
#                         if v1_time_str != v2_time_str:
#                             time_differs = True
#                     else:
#                         # Compare other values
#                         v1_val = v1_record.get(key)
#                         v2_val = v2_record.get(key)
#                         if v1_val != v2_val:
#                             record_differs = True
#                             break

#                 if record_differs:
#                     data_mismatches += 1
#                     if data_mismatches <= 2:  # Show first 2 data mismatches
#                         print(f"Data mismatch in record {i}:")
#                         print(f"  V1: {v1_record}")
#                         print(f"  V2: {v2_record}")

#                 if time_differs:
#                     mismatches += 1

#             # Report results
#             if data_mismatches == 0 and mismatches == 0:
#                 print("✅ All data and timestamps match perfectly!")
#             elif data_mismatches == 0:
#                 print(f"✅ All data values match perfectly!")
#                 print(
#                     f"ℹ️  Time formats differ but represent same moments ({mismatches} records)"
#                 )
#             else:
#                 print(f"❌ Found {data_mismatches} records with data mismatches")
#                 if data_mismatches > 2:
#                     print(f"... (showing first 2 data mismatches)")

#         except Exception as e:
#             print(f"❌ Error comparing data: {e}")
#             import traceback

#             traceback.print_exc()

#         # Test different intervals
#         print("\n🔄 Testing different intervals...")
#         intervals_to_test = ["30 minutes", "2 hours", "1 day"]

#         for test_interval in intervals_to_test:
#             print(f"\nTesting interval: {test_interval}")

#             # V1
#             with with_db(schema=project_name_short) as project_db:
#                 v1_test = get_project_data_timeseries(
#                     project_db=project_db,
#                     project_name_short=project_name_short,
#                     tag_ids=[1],  # Single tag for faster testing
#                     start=start,
#                     end=end,
#                     interval=test_interval,
#                     cagg_interval=cagg_interval,
#                 )
#                 v1_test_pandas_df = v1_test.pandas_dataframe()
#                 v1_test_data = [
#                     row.to_dict() for _, row in v1_test_pandas_df.iterrows()
#                 ]

#             # V2
#             v2_test = get_project_data_timeseries_v2(
#                 project_name_short=project_name_short,
#                 tag_ids=[1],
#                 start=start,
#                 end=end,
#                 interval=test_interval,
#                 cagg_interval=cagg_interval,
#                 return_query=True,
#             )
#             v2_test_df = await v2_test.polars_dataframe_async()
#             v2_test_data = v2_test_df.to_dicts()

#             # Both should use 'time' column now, no normalization needed

#             # Compare record counts and basic data values
#             if len(v1_test_data) == len(v2_test_data):
#                 # Quick data comparison (compare first few non-time values)
#                 data_match = True
#                 if v1_test_data and v2_test_data:
#                     for key in ["tag_id", "value_double", "value_integer"]:
#                         if key in v1_test_data[0] and key in v2_test_data[0]:
#                             if v1_test_data[0][key] != v2_test_data[0][key]:
#                                 data_match = False
#                                 break

#                 if data_match:
#                     print(
#                         f"  ✅ {test_interval}: Results match (records: {len(v1_test_data)})"
#                     )
#                 else:
#                     print(
#                         f"  ❌ {test_interval}: Data values differ (records: {len(v1_test_data)})"
#                     )
#             else:
#                 print(
#                     f"  ❌ {test_interval}: Record counts differ (V1: {len(v1_test_data)}, V2: {len(v2_test_data)})"
#                 )

#     # Run the comparison test
#     asyncio.run(compare_v1_and_v2())
