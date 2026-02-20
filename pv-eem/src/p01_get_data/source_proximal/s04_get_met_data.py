import logging
from datetime import UTC, datetime, timedelta

import polars as pl
import pytz
import sqlalchemy
from p01_get_data._utils import QueryType, switch_column_name


async def get_met_data(
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
    _ = ENVIRONMENT

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

    column_name: str | pl.DataFrame = switch_column_name(
        query_type=QueryType.MET_STATION,
        project_name_short=project_name_short,
        project_data_table_name=project_data_table_name,
        engine=engine,
    )

    metadata = sqlalchemy.MetaData()
    data = sqlalchemy.Table(
        project_data_table_name,
        metadata,
        schema=project_name_short,
        autoload_with=engine,
    )
    tags = sqlalchemy.Table(
        "tags",
        metadata,
        schema=project_name_short,
        autoload_with=engine,
    )
    sensor_type = sqlalchemy.Table(
        "sensor_types",
        metadata,
        schema="operational",
        autoload_with=engine,
    )
    devices = sqlalchemy.Table(
        "devices",
        metadata,
        schema=project_name_short,
        autoload_with=engine,
    )

    bucketed_time = sqlalchemy.func.time_bucket(
        sqlalchemy.text("'5 minutes'"),
        data.c.time,
    )
    joined_tables = (
        data.outerjoin(tags, data.c.tag_id == tags.c.tag_id)
        .outerjoin(sensor_type, tags.c.sensor_type_id == sensor_type.c.sensor_type_id)
        .outerjoin(devices, tags.c.device_id == devices.c.device_id)
    )

    if isinstance(column_name, pl.DataFrame):
        sensor_values = column_name.select("sensor_name", "data_column_name").rows()

        case_conditions = []
        sensor_names = []
        for sensor, col_type in sensor_values:
            data_column_name = f"value_{col_type}"
            case_conditions.append(
                (sensor_type.c.name_short == sensor, data.c[data_column_name])
            )
            sensor_names.append(sensor)

        case_expression = sqlalchemy.case(*case_conditions, else_=None)

        query = (
            sqlalchemy.select(
                bucketed_time.label("time"),
                sqlalchemy.func.avg(case_expression).label("value_continuous"),
                sensor_type.c.name_short.label("sensor_name"),
                sensor_type.c.unit,
                devices.c.name_short.label("met_name"),
            )
            .select_from(joined_tables)
            .where(
                data.c.time >= start,
                data.c.time <= end,
                case_expression.is_not(None),
                sensor_type.c.name_short.in_(sensor_names),
            )
            .group_by(
                bucketed_time,
                sensor_type.c.name_short,
                sensor_type.c.unit,
                devices.c.name_short,
            )
            .order_by(
                bucketed_time,
                devices.c.name_short,
                sensor_type.c.name_short,
            )
        )
    elif isinstance(column_name, str):
        sensor_names = [
            "met_station_poa",
            "met_station_poa_tilt",
            "met_station_ghi",
            "met_station_ghi_tilt",
            "met_station_ambient_temperature",
            "met_station_wind_speed",
            "met_station_relative_humidity",
        ]
        column_expression = data.c[column_name]
        query = (
            sqlalchemy.select(
                bucketed_time.label("time"),
                sqlalchemy.func.avg(column_expression).label("value_continuous"),
                sensor_type.c.name_short.label("sensor_name"),
                sensor_type.c.unit,
                devices.c.name_short.label("met_name"),
            )
            .select_from(joined_tables)
            .where(
                data.c.time >= start,
                data.c.time <= end,
                column_expression.is_not(None),
                sensor_type.c.name_short.in_(sensor_names),
            )
            .group_by(
                bucketed_time,
                sensor_type.c.name_short,
                sensor_type.c.unit,
                devices.c.name_short,
            )
            .order_by(
                bucketed_time,
                devices.c.name_short,
                sensor_type.c.name_short,
            )
        )

    else:
        raise ValueError("column_name switch must be a string or a polars DataFrame")

    # --- Execute query ---
    with engine.connect() as conn:
        met_data: pl.DataFrame = pl.read_database(
            query=query,
            connection=conn,
        )

    return met_data
