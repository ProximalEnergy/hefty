from datetime import UTC, datetime, timedelta

import polars as pl
import pytz
import sqlalchemy
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.crud.project.query_metadata_cache import get_project_tags_cached
from core.enumerations import (
    AggregationMethod,
    DeviceType,
    SensorType,
    TimeInterval,
    TimeOffset,
)
from p02_simulation.p3_epoai.s05_soiling import ModelSoiling
from sqlalchemy.orm import Session

SOILING_SENSOR_TYPE_IDS = SensorType.extract_values(
    enum_list=[
        SensorType.MET_STATION_POA,
        SensorType.MET_STATION_GHI,
        SensorType.MET_STATION_SOIL_PERCENT,
    ]
)


def _empty_soiling_data() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "time": pl.Datetime,
            "value_continuous": pl.Float64,
            "sensor_name": pl.String,
            "unit": pl.String,
            "met_name": pl.String,
        }
    )


async def get_met_soiling(
    *,
    model_soiling: ModelSoiling,
    project_name_short: str,
    project_data_table_name: str,
    time_zone: str,
    simulation_temporal_mode: str,
    simulation_start: str,
    simulation_end: str,
    engine: sqlalchemy.engine.Engine,
    ENVIRONMENT: str,
) -> pl.DataFrame:
    """Load relevant met-station soiling and irradiance data into memory."""
    _ = model_soiling, ENVIRONMENT, project_data_table_name

    start_time_naive = datetime.strptime(simulation_start, "%Y-%m-%d %H:%M:%S")
    end_time_naive = datetime.strptime(simulation_end, "%Y-%m-%d %H:%M:%S")

    tz = pytz.timezone(time_zone)
    start_time_aware = tz.localize(start_time_naive)
    end_time_aware = tz.localize(end_time_naive)

    start_time_utc = start_time_aware.astimezone(pytz.utc)
    end_time_utc = end_time_aware.astimezone(pytz.utc)

    match simulation_temporal_mode:
        case "window":
            start = start_time_utc - timedelta(hours=24)
            end = end_time_utc
        case "instantaneous":
            end = datetime.now(UTC)
            start = end - timedelta(hours=24)
        case _:
            raise ValueError("simulation_temporal_mode must be window | instantaneous")

    tags = await get_project_tags_cached(
        project_name_short=project_name_short,
        device_type_ids=[DeviceType.MET_STATION],
        sensor_type_ids=SOILING_SENSOR_TYPE_IDS,
        deep=True,
    )

    if tags.is_empty():
        return _empty_soiling_data()

    with Session(bind=engine) as project_db:
        data_timeseries = await DataTimeseries(
            project_name_short=project_name_short,
            filter_method=FilterMethod.TAG_POLARS,
            filter_values=tags,
            query_start=start,
            query_end=end + timedelta(microseconds=1),
            project_db=project_db,
            max_lookback_period=TimeOffset.NONE,
            freq=TimeInterval.FIVE_MINUTES,
            aggregation_method=AggregationMethod.AVERAGE,
            ffill_limit=0,
            ensure_full_range=False,
        ).get()

    soiling_data = data_timeseries.df
    value_columns = [column for column in soiling_data.columns if column != "time"]

    if soiling_data.is_empty() or not value_columns:
        return _empty_soiling_data()

    time_dtype = soiling_data.schema["time"]
    if isinstance(time_dtype, pl.Datetime) and time_dtype.time_zone is not None:
        soiling_data = soiling_data.with_columns(
            pl.col("time")
            .dt.convert_time_zone("UTC")
            .dt.replace_time_zone(None)
            .alias("time")
        )

    soiling_data = (
        soiling_data.unpivot(
            index="time",
            on=value_columns,
            variable_name="tag_id",
            value_name="value_continuous",
        )
        .with_columns(
            pl.col("tag_id").cast(pl.Int64, strict=False),
            pl.col("value_continuous").cast(pl.Float64, strict=False),
        )
        .drop_nulls(subset=["tag_id", "value_continuous"])
        .join(
            tags.select(
                [
                    pl.col("tag_id").cast(pl.Int64),
                    "sensor_type_name_short",
                    "sensor_type_unit",
                    "device_name_short",
                ]
            ),
            on="tag_id",
            how="inner",
        )
        .group_by(
            [
                "time",
                "sensor_type_name_short",
                "sensor_type_unit",
                "device_name_short",
            ]
        )
        .agg(pl.col("value_continuous").mean().alias("value_continuous"))
        .rename(
            {
                "sensor_type_name_short": "sensor_name",
                "sensor_type_unit": "unit",
                "device_name_short": "met_name",
            }
        )
        .select(["time", "value_continuous", "sensor_name", "unit", "met_name"])
        .sort(["time", "met_name", "sensor_name"])
    )

    return soiling_data
