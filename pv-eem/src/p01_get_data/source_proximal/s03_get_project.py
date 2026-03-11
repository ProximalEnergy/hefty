from dataclasses import dataclass

import polars as pl
from core.db_query import DbQuery, OutputType
from sqlalchemy import bindparam, text


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

    @classmethod
    async def create(
        cls,
        *,
        project_name_short: str,
    ) -> "Project":
        """Load project metadata and build a project instance.

        Args:
            project_name_short: Project short name to load.

        Returns:
            Hydrated project metadata instance.

        Raises:
            ValueError: If the project is missing or `cod` is null.
        """
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
        ).bindparams(
            bindparam(
                "project_name_short",
                value=project_name_short,
            )
        )
        project_polars: pl.DataFrame = await DbQuery(query=query_project).get_async(
            schema=None,
            output_type=OutputType.POLARS,
        )

        if project_polars.is_empty():
            raise ValueError(f"Project '{project_name_short}' not found in database")

        project = project_polars.row(0, named=True)
        if project["cod"] is None:
            raise ValueError("cod in operational.projects must not be null")

        obj = cls.__new__(cls)
        obj.name_short = str(project["name_short"])
        obj.name_long = str(project["name_long"])
        obj.data_table = str(project["data_table"])
        obj.time_zone = str(project["time_zone"])
        obj.poi_limit = float(project["poi"])
        obj.longitude = float(project["longitude"])
        obj.latitude = float(project["latitude"])
        obj.elevation = float(project["elevation"])
        obj.cod = str(project["cod"])
        return obj
