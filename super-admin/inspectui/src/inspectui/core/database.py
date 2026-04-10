"""Database connection manager using psycopg2."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

# Load environment variables
load_dotenv(override=True)


class DatabaseManager:
    """Manages database connections using psycopg2."""

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize the database manager.

        Args:
            database_url: Connection string, or None to use ``DATABASE_URL``
                from the environment.

        Raises:
            ValueError: If DATABASE_URL is not set.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if self.database_url is None:
            raise ValueError("DATABASE_URL is not set")

        # Test connection
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

    @contextmanager
    def get_connection(self) -> Iterator[psycopg2.extensions.connection]:
        """Get a database connection as a context manager."""
        conn = psycopg2.connect(self.database_url)
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a query and return results as a list of dictionaries.

        Args:
            query: SQL query to execute.
            params: Optional query parameters.

        Returns:
            List of dictionaries, one per row.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]

    def execute_query_with_schema(
        self,
        query: str,
        schema: str,
        params: tuple[Any, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a query with a specific schema set.

        Args:
            query: SQL query to execute.
            schema: Schema name to set before executing.
            params: Optional query parameters.

        Returns:
            List of dictionaries, one per row.
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("SET search_path TO {}, public").format(
                        sql.Identifier(schema),
                    ),
                )
                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
