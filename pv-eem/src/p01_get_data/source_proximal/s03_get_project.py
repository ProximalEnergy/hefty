from dataclasses import dataclass

import pandas as pd
import polars as pl
import sqlalchemy
from sqlalchemy import text


@dataclass(init=False, slots=True)
class Project:
    """Project."""

    name_short: str
    name_long: str
    data_table: str  # name of the db table where to find timeseries data
    time_zone: str
    poi_limit: float  # grid injection limit
    longitude: float
    latitude: float
    elevation: float
    cod: str

    def __init__(
        self,
        project_name_short: str,
        engine: sqlalchemy.engine.Engine,
    ):
        # --- Execution ---
        # Get all PV and PV+Storage projects
        query_project = text(
            """
            SELECT
                p.name_short,
                p.name_long,
                p.data_table,
                p.time_zone,
                p.poi,
                ST_X(p.point::geometry) as longitude,
                ST_Y(p.point::geometry) as latitude,
                p.elevation,
                p.cod
            FROM operational.projects AS p
            WHERE p.name_short = :project_name_short
        """
        )
        # Database Call
        with engine.connect() as conn:
            project_polars: pl.DataFrame = pl.read_database(
                query=query_project,
                connection=conn,
                execute_options={
                    "parameters": {"project_name_short": project_name_short}
                },
            )

        # --- QA ---
        if project_polars.is_empty():
            raise ValueError(f"Project '{project_name_short}' not found in database")
        if project_polars.row(0, named=True)["cod"] is None:
            raise ValueError("cod in operational.projects must not be null")

        # Convert to pandas
        project: pd.DataFrame = project_polars.to_pandas()

        self.name_short = project.iloc[0]["name_short"]
        self.name_long = project.iloc[0]["name_long"]
        self.data_table = project.iloc[0]["data_table"]
        self.time_zone = project.iloc[0]["time_zone"]
        self.poi_limit = project.iloc[0]["poi"]
        self.longitude = project.iloc[0]["longitude"]
        self.latitude = project.iloc[0]["latitude"]
        self.elevation = project.iloc[0]["elevation"]
        self.cod = project.iloc[0]["cod"]
