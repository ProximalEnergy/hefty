from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload, noload
from sqlalchemy.orm.strategy_options import _AbstractLoad

from core import enumerations, models
from core.db_query import DbQuery


def get_project_options(*, deep: bool) -> _AbstractLoad:
    """Return loader options for project queries.

    Args:
        deep: Whether to eager-load related project type data.
    """
    if deep:
        options = joinedload(models.Project.project_type)
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
    """Build a query for projects with optional filters.

    Args:
        project_ids: Project ids to filter by.
        project_type_ids: Project type ids to filter by.
        project_status_type_ids: Status types to filter by.
        name_short: Filter by name_short.
        name_shorts: Filter by a list of name_short values.
        name_long: Filter by name_long.
        has_pv_pcs_modules: Filter by PV/PCS module presence.
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
    """Build a query for a single project by id.

    Args:
        project_id: Project id to fetch.
        deep: Whether to eager-load related project type data.
    """
    options = get_project_options(deep=deep)
    stmt = (
        select(models.Project)
        .options(options)
        .where(models.Project.project_id == project_id)
    )
    return DbQuery(query=stmt, is_scalar=True)
