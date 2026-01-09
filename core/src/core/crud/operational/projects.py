from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload
from sqlalchemy.orm.strategy_options import _AbstractLoad

from core import enumerations, models
from core.db_query import DbQuery


def get_project_options(*, deep: bool) -> _AbstractLoad:
    """TODO: add description.

    Args:
        deep: TODO: describe.
    """
    if deep:
        options = selectinload(models.Project.project_type)
    else:
        options = noload(models.Project.project_type)

    return options


def get_projects(
    *,
    project_ids: list[UUID] | None = None,
    project_type_ids: list[int] | None = None,
    project_status_type_ids: list[enumerations.ProjectStatusType] | None = [
        enumerations.ProjectStatusType.ACTIVE
    ],
    name_short: str | None = None,
    name_shorts: list[str] | None = None,
    name_long: str | None = None,
    has_pv_pcs_modules: bool | None = None,
) -> DbQuery[models.Project, Literal[False]]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        deep: TODO: describe.
        project_ids: TODO: describe.
        project_type_ids: TODO: describe.
        project_status_type_ids: TODO: describe.
        name_short: TODO: describe.
        name_shorts: TODO: describe.
        name_long: TODO: describe.
        has_pv_pcs_modules: TODO: describe.
        return_query: TODO: describe.
    """
    stmt = select(models.Project)

    if project_ids is not None:
        stmt = stmt.where(models.Project.project_id.in_(project_ids))
    if project_type_ids is not None:
        stmt = stmt.where(models.Project.project_type_id.in_(project_type_ids))
    if project_status_type_ids is not None:
        status_ids = enumerations.ProjectStatusType.extract_values(
            enum_list=project_status_type_ids
        )
        stmt = stmt.where(models.Project.project_status_type_id.in_(status_ids))
    if name_short is not None:
        stmt = stmt.where(models.Project.name_short == name_short)
    if name_shorts is not None:
        stmt = stmt.where(models.Project.name_short.in_(name_shorts))
    if name_long is not None:
        stmt = stmt.where(models.Project.name_long == name_long)
    if has_pv_pcs_modules is not None:
        stmt = stmt.where(models.Project.has_pv_pcs_modules == has_pv_pcs_modules)

    return DbQuery(query=stmt)


def get_project(
    *, project_id: UUID, deep: bool = False
) -> DbQuery[models.Project, Literal[True]]:
    """TODO: add description.

    Args:
        project_id: TODO: describe.
        deep: TODO: describe.
    """
    options = get_project_options(deep=deep)
    stmt = (
        select(models.Project)
        .options(options)
        .where(models.Project.project_id == project_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


async def get_project_timezone_and_data_cagg_interval_by_name_short_async(
    *, db: AsyncSession, name_short: str
) -> dict[str, str | None] | None:
    """
    Get timezone and data_cagg_interval for a project by name_short.

    Args:
        db (AsyncSession): The database session to use for the query.
        name_short (str): The project name_short to look up.

    Returns:
        dict[str, str | None] | None: A dictionary containing timezone and
            data_cagg_interval, or None if project not found.
    """
    stmt = select(
        models.Project.time_zone,
        models.Project.data_cagg_interval,
    ).where(models.Project.name_short == name_short)

    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        return None

    return {
        "timezone": row.time_zone,
        "data_cagg_interval": row.data_cagg_interval,
    }
