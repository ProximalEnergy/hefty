import functools
from collections.abc import Callable

from alembic import op
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError


def for_each_project_schema(func: Callable) -> Callable:
    """Run ``func`` once per project schema listed in ``operational.projects``.

    Args:
        func: Callable taking the project ``name_short`` (PostgreSQL schema name).

    Missing PostgreSQL schemas are skipped. Each run uses a savepoint so a
    skipped schema does not leave the migration connection in an aborted
    transaction.
    """

    @functools.wraps(func)
    def wrapped():
        bind = op.get_bind()
        schemas = bind.execute(
            text("SELECT name_short FROM operational.projects"),
        ).fetchall()
        for (schema,) in schemas:
            try:
                with bind.begin_nested():
                    func(schema)
            except ProgrammingError as exc:
                orig = getattr(exc, "orig", None)
                pgcode = getattr(orig, "pgcode", None)
                msg = str(orig or exc)
                is_missing_schema = pgcode == "3F000" or (
                    "schema" in msg.lower() and "does not exist" in msg.lower()
                )
                if not is_missing_schema:
                    raise

    return wrapped
