from enum import Enum

import polars as pl
import sqlalchemy


class QueryType(Enum):
    MET_STATION = 1
    SOILING = 2


def switch_column_name(
    query_type: QueryType,
    project_name_short: str,
    project_data_table_name: str,
    engine: sqlalchemy.engine.Engine,
) -> str | pl.DataFrame:
    # --- match on data_table ---
    match project_data_table_name:
        case "data":
            column_name = "value_continuous"
        case "data_raw":
            column_name = "value_continuous"
        case "data_timeseries":
            metadata = sqlalchemy.MetaData()
            tags = sqlalchemy.Table(
                "tags",
                metadata,
                schema=project_name_short,
                autoload_with=engine,
            )
            pg_data_types = sqlalchemy.Table(
                "pg_data_types",
                metadata,
                schema="operational",
                autoload_with=engine,
            )
            sensor_type = sqlalchemy.Table(
                "sensor_types",
                metadata,
                schema="operational",
                autoload_with=engine,
            )

            if query_type == QueryType.MET_STATION:
                sensor_names = [
                    "met_station_poa",
                    "met_station_poa_tilt",
                    "met_station_ghi",
                    "met_station_ghi_tilt",
                    "met_station_ambient_temperature",
                    "met_station_wind_speed",
                    "met_station_relative_humidity",
                ]
            elif query_type == QueryType.SOILING:
                sensor_names = [
                    "met_station_soil_percent",
                    "met_station_ghi",
                    "met_station_poa",
                ]
            else:
                raise ValueError(f"query_type must be in {QueryType}")

            query = (
                sqlalchemy.select(
                    tags.c.tag_id.label("tag_id"),
                    sensor_type.c.name_short.label("sensor_name"),
                    pg_data_types.c.name_short.label("data_column_name"),
                )
                .select_from(
                    tags.outerjoin(
                        pg_data_types,
                        tags.c.pg_data_type_id == pg_data_types.c.pg_data_type_id,
                    ).outerjoin(
                        sensor_type,
                        tags.c.sensor_type_id == sensor_type.c.sensor_type_id,
                    )
                )
                .where(sensor_type.c.name_short.in_(sensor_names))
                .distinct(sensor_type.c.name_short)
            )

            with engine.connect() as conn:
                column_name_df = pl.read_database(
                    query=query,
                    connection=conn,
                )
                return column_name_df

        case _:
            raise ValueError(
                "project_data_table_name must be 'data' or 'data_raw' or "
                "'data_timeseries'"
            )

    return column_name
