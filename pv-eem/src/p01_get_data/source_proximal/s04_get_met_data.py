import logging
from datetime import UTC, datetime, timedelta

import polars as pl
import pytz
import sqlalchemy
from dotenv import load_dotenv
from sqlalchemy.orm import Session

load_dotenv()

from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.crud.project.query_metadata_cache import get_project_tags_cached
from core.enumerations import (
    AggregationMethod,
    DeviceTypeEnum,
    SensorTypeEnum,
    TimeInterval,
    TimeOffset,
)

MET_SENSOR_TYPE_IDS = SensorTypeEnum.extract_values(
    enum_list=[
        SensorTypeEnum.MET_STATION_POA,
        SensorTypeEnum.MET_STATION_POA_TILT,
        SensorTypeEnum.MET_STATION_GHI,
        SensorTypeEnum.MET_STATION_GHI_TILT,
        SensorTypeEnum.MET_STATION_AMBIENT_TEMPERATURE,
        SensorTypeEnum.MET_STATION_WIND_SPEED,
        SensorTypeEnum.MET_STATION_RELATIVE_HUMIDITY,
    ]
)


def _empty_met_data() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "time": pl.Datetime,
            "value_continuous": pl.Float64,
            "sensor_name": pl.String,
            "unit": pl.String,
            "met_name": pl.String,
        }
    )


async def get_met_data(
    *,
    time_zone: str,
    project_name_short: str,
    project_data_table_name: str,
    simulation_temporal_mode: str,
    simulation_start: str,
    simulation_end: str,
    engine: sqlalchemy.engine.Engine,
    ENVIRONMENT: str,
):
    # --- Calc start and end in UTC ---
    # Convert to datetime.datetime object
    """Run get_met_data."""
    _ = ENVIRONMENT, project_data_table_name

    start_time_naive = datetime.strptime(simulation_start, "%Y-%m-%d %H:%M:%S")
    end_time_naive = datetime.strptime(simulation_end, "%Y-%m-%d %H:%M:%S")

    # localize to project time zone
    tz = pytz.timezone(time_zone)
    start_time_aware = tz.localize(start_time_naive)
    end_time_aware = tz.localize(end_time_naive)

    # convert to UTC
    start_time_utc = start_time_aware.astimezone(pytz.utc)
    end_time_utc = end_time_aware.astimezone(pytz.utc)

    # --- Get start and end ---
    match simulation_temporal_mode:
        # --- WINDOW ---
        case "window":
            start = start_time_utc
            end = end_time_utc

        # --- INSTANTANEOUS ---
        case "instantaneous":
            # Get the current time
            now = datetime.now(UTC)

            # Calculate the end time: truncate to the last 5-minute interval
            end_dt = now.replace(minute=(now.minute // 5) * 5, second=0, microsecond=0)

            # Calculate the start time: 14 minutes-ish before the end time
            # CANNOT be exactly five minutes or you will get duplicate entries
            start = end_dt - timedelta(minutes=14, seconds=30)
            end = end_dt
            logging.info(f"instantaneous ends: {end}")
        case _:
            raise ValueError("simulation_temporal_mode must be window | instantaneous")

    tags = await get_project_tags_cached(
        project_name_short=project_name_short,
        device_type_ids=[DeviceTypeEnum.MET_STATION],
        sensor_type_ids=MET_SENSOR_TYPE_IDS,
        deep=True,
    )
    logging.debug("MET tag preview:\n%s", tags.head())

    if tags.is_empty():
        return _empty_met_data()

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

    met_data = data_timeseries.df
    value_columns = [column for column in met_data.columns if column != "time"]

    if met_data.is_empty() or not value_columns:
        return _empty_met_data()

    time_dtype = met_data.schema["time"]
    if isinstance(time_dtype, pl.Datetime) and time_dtype.time_zone is not None:
        met_data = met_data.with_columns(
            pl.col("time")
            .dt.convert_time_zone("UTC")
            .dt.replace_time_zone(None)
            .alias("time")
        )

    met_data = (
        met_data.unpivot(
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
    logging.debug("MET data preview:\n%s", met_data.head())

    return met_data
