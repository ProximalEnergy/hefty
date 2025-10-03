import functools
from collections.abc import Callable

from alembic import op
from sqlalchemy import text


def for_each_project_schema(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapped():
        schemas = (
            op.get_bind()
            .execute(text("SELECT name_short FROM operational.projects"))
            .fetchall()
        )
        for (schema,) in schemas:
            func(schema)

    return wrapped
