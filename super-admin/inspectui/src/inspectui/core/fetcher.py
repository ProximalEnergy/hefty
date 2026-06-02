"""Data fetcher for loading projects, devices, and tags from the database."""

from typing import Any

import psycopg2.errors

from inspectui.core.database import DatabaseManager
from inspectui.core.models import DeviceInfo, ProjectInfo, TagInfo


class DataFetcher:
    """Fetches data from the database."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    def _fetch_schema_rows(
        self,
        *,
        query: str,
        project_name_short: str,
    ) -> list[dict[str, Any]]:
        """Run a schema-scoped query; return [] if the table is missing."""
        try:
            return self.db.execute_query_with_schema(query, project_name_short)
        except psycopg2.errors.UndefinedTable:
            return []

    def _project_name_shorts_with_device_tag_tables(self) -> set[str]:
        """Return name_shorts whose schema has both devices and tags tables."""
        query = """
            SELECT p.name_short
            FROM operational.projects p
            WHERE EXISTS (
                SELECT 1
                FROM information_schema.tables t
                WHERE t.table_schema = p.name_short
                  AND t.table_name = 'devices'
            )
            AND EXISTS (
                SELECT 1
                FROM information_schema.tables t
                WHERE t.table_schema = p.name_short
                  AND t.table_name = 'tags'
            )
        """
        rows = self.db.execute_query(query)
        return {row["name_short"] for row in rows}

    def filter_projects_with_device_tag_tables(
        self,
        *,
        projects: list[ProjectInfo],
    ) -> list[ProjectInfo]:
        """Keep projects whose schema has devices and tags tables.

        Args:
            projects: Project rows to filter.

        Returns:
            Subset of ``projects`` with both per-schema tables present.
        """
        valid = self._project_name_shorts_with_device_tag_tables()
        return [p for p in projects if p.name_short in valid]

    def fetch_all_projects(self) -> list[ProjectInfo]:
        """Fetch projects that have devices and tags tables.

        Returns:
            List of ProjectInfo objects sorted by name_short.
        """
        query = """
            SELECT project_id, project_id_int, name_short, name_long,
                   data_table, project_type_id, project_status_type_id,
                   capacity_dc, capacity_ac, cod, time_zone
            FROM operational.projects p
            WHERE EXISTS (
                SELECT 1
                FROM information_schema.tables t
                WHERE t.table_schema = p.name_short
                  AND t.table_name = 'devices'
            )
            AND EXISTS (
                SELECT 1
                FROM information_schema.tables t
                WHERE t.table_schema = p.name_short
                  AND t.table_name = 'tags'
            )
            ORDER BY name_short
        """
        rows = self.db.execute_query(query)
        return [
            ProjectInfo(
                project_id=row["project_id"],
                project_id_int=row["project_id_int"],
                name_short=row["name_short"],
                name_long=row["name_long"],
                data_table=row["data_table"],
                project_type_id=row["project_type_id"],
                project_status_type_id=row["project_status_type_id"],
                capacity_dc=row["capacity_dc"],
                capacity_ac=row["capacity_ac"],
                cod=row["cod"],
                time_zone=row["time_zone"],
            )
            for row in rows
        ]

    def fetch_devices(self, project_name_short: str) -> list[DeviceInfo]:
        """Fetch all devices for a project.

        Args:
            project_name_short: The project's short name (schema name).

        Returns:
            List of DeviceInfo objects sorted by device_id.
        """
        query = """
            SELECT device_id, device_type_id, name_short, name_long,
                   parent_device_id, capacity_dc, capacity_ac,
                   capacity_energy_dc, device_model_id
            FROM devices
            ORDER BY device_id
        """
        rows = self._fetch_schema_rows(
            query=query,
            project_name_short=project_name_short,
        )
        return [
            DeviceInfo(
                device_id=row["device_id"],
                device_type_id=row["device_type_id"],
                name_short=row["name_short"],
                name_long=row["name_long"],
                parent_device_id=row["parent_device_id"],
                capacity_dc=row["capacity_dc"],
                capacity_ac=row["capacity_ac"],
                capacity_energy_dc=row["capacity_energy_dc"],
                device_model_id=row["device_model_id"],
            )
            for row in rows
        ]

    def fetch_tags(self, project_name_short: str) -> list[TagInfo]:
        """Fetch all tags for a project.

        Args:
            project_name_short: The project's short name (schema name).

        Returns:
            List of TagInfo objects sorted by tag_id.
        """
        query = """
            SELECT tag_id, device_id, sensor_type_id, data_type_id,
                   name_short, name_long, name_scada, in_tsdb
            FROM tags
            ORDER BY tag_id
        """
        rows = self._fetch_schema_rows(
            query=query,
            project_name_short=project_name_short,
        )
        return [
            TagInfo(
                tag_id=row["tag_id"],
                device_id=row["device_id"],
                sensor_type_id=row["sensor_type_id"],
                data_type_id=row["data_type_id"],
                name_short=row["name_short"],
                name_long=row["name_long"],
                name_scada=row["name_scada"],
                in_tsdb=row["in_tsdb"],
            )
            for row in rows
        ]
