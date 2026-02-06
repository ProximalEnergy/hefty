from functools import lru_cache
from typing import Any, Literal, cast
from uuid import UUID

from async_lru import alru_cache
from sqlalchemy import select

from core import models
from core.db_query import DbQuery
from core.enumerations import OutputType


def get_project_name_short_query(*, project_id: UUID) -> DbQuery[Any, Literal[True]]:
    """Get project name short query.

    Args:
        project_id: UUID of the project to look up.
    """

    stmt = select(models.Project.name_short).where(
        models.Project.project_id == project_id
    )
    return DbQuery(query=stmt, is_scalar=True)


@lru_cache(maxsize=128)
def get_project_name_short(*, project_id: UUID) -> str | None:
    """Lookup a project's short name by project id.

    Args:
        project_id: UUID of the project to look up.
    """
    return cast(
        str | None,
        get_project_name_short_query(project_id=project_id).get(
            schema=None, output_type=OutputType.SQLALCHEMY
        ),
    )


@alru_cache(maxsize=128)
async def get_project_name_short_async(*, project_id: UUID) -> str | None:
    """Lookup a project's short name asynchronously by project id.

    Args:
        project_id: UUID of the project to look up.
    """
    return cast(
        str | None,
        await get_project_name_short_query(project_id=project_id).get_async(
            schema=None, output_type=OutputType.SQLALCHEMY
        ),
    )
