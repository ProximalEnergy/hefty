from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import load_only, noload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from core import enumerations, models
from core.db_query import DbQuery

ProjectAttribute = InstrumentedAttribute[Any]
type ProjectColumns = tuple[ProjectAttribute, ...]
_ALL_PROJECT_COLUMNS: ProjectColumns = tuple(
    getattr(models.Project, column.name) for column in models.Project.__table__.columns
)


@dataclass(frozen=True, kw_only=True)
class JoinedProjectColumn:
    column: InstrumentedAttribute[Any]
    label: str


type JoinedProjectColumns = tuple[JoinedProjectColumn, ...]


JOINED_PROJECT_TYPE = JoinedProjectColumn(
    column=models.ProjectType.name_short,
    label="project_type",
)


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
    *,
    project_id: UUID,
    columns: ProjectColumns | None = None,
    joined_columns: JoinedProjectColumns = (),
) -> DbQuery[Any, Literal[True]]:
    """Build a query for a single project by id.

    Args:
        project_id: Project id to fetch.
        columns: Optional subset of Project columns to load. ``None`` loads all
            project columns. When projecting only joined columns, pass ``()``.
        joined_columns: Optional configured joined columns to project. When
            ``JOINED_PROJECT_TYPE`` is included, dataframe outputs expose
            ``ProjectType.name_short`` as ``project_type`` and SQLAlchemy
            output returns a projected row mapping.
    """
    if not joined_columns:
        if not columns:
            stmt = (
                select(models.Project)
                .options(noload(models.Project.project_type))
                .where(models.Project.project_id == project_id)
            )
        else:
            stmt = (
                select(models.Project)
                .options(
                    noload(models.Project.project_type),
                    load_only(*columns),
                )
                .where(models.Project.project_id == project_id)
            )
    else:
        projected_columns = []
        for column in _ALL_PROJECT_COLUMNS if columns is None else columns:
            projected_columns.append(column.label(column.key))
        for joined_column in joined_columns:
            projected_columns.append(joined_column.column.label(joined_column.label))

        stmt = select(*projected_columns).select_from(models.Project)
        for joined_column in joined_columns:
            stmt = stmt.outerjoin(joined_column.column.class_)
        stmt = stmt.where(models.Project.project_id == project_id)

    return DbQuery(query=stmt, is_scalar=True)
