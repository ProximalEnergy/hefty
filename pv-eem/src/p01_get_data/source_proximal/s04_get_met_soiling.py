import datetime

import polars as pl
import pytz
import sqlalchemy
from p01_get_data._utils import QueryType, switch_column_name
from p02_simulation.p3_epoai.s05_soiling import ModelSoiling


async def get_met_soiling(
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
    """Load relevant soiling data into memory for the last day
    Args:
        * project_name_short:  name_short in the project
        * DB_URI: Database URI
    """
    _ = model_soiling
    _ = ENVIRONMENT

    # --- Calc start and end in UTC ---
    # Convert to datetime.datetime object
    start_time_naive = datetime.datetime.strptime(simulation_start, "%Y-%m-%d %H:%M:%S")
    end_time_naive = datetime.datetime.strptime(simulation_end, "%Y-%m-%d %H:%M:%S")

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
            start = start_time_utc - datetime.timedelta(hours=24)
            end = end_time_utc

        # --- INSTANTANEOUS ---
        case "instantaneous":
            end = datetime.datetime.now(datetime.UTC)
            start = end - datetime.timedelta(hours=24)
        case _:
            raise ValueError("simulation_temporal_mode must be window | instantaneous")

    column_name: pl.DataFrame | str = switch_column_name(
        query_type=QueryType.SOILING,
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
            "met_station_soil_percent",
            "met_station_ghi",
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

    with engine.connect() as conn:
        soiling_data = pl.read_database(
            query=query,
            connection=conn,
        )

    return soiling_data
