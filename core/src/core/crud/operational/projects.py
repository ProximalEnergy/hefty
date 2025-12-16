from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, noload, selectinload
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.strategy_options import _AbstractLoad

from core import enumerations, models
from core.model_list import ModelItem, ModelList


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
    db: Session,
    *,
    deep: bool = False,
    project_ids: list[UUID] | None = None,
    project_type_ids: list[int] | None = None,
    project_status_type_ids: list[enumerations.ProjectStatusType] | None = [
        enumerations.ProjectStatusType.ACTIVE
    ],
    name_short: str | None = None,
    name_shorts: list[str] | None = None,
    name_long: str | None = None,
    has_pv_pcs_modules: bool | None = None,
    return_query: bool = False,
) -> ModelList[models.Project]:
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
    options = get_project_options(deep=deep)

    query = db.query(models.Project).options(options)

    if project_ids is not None:
        query = query.filter(models.Project.project_id.in_(project_ids))
    if project_type_ids is not None:
        query = query.filter(models.Project.project_type_id.in_(project_type_ids))
    if project_status_type_ids is not None:
        status_ids = enumerations.ProjectStatusType.extract_values(
            project_status_type_ids
        )
        query = query.filter(models.Project.project_status_type_id.in_(status_ids))
    if name_short is not None:
        query = query.filter(models.Project.name_short == name_short)
    if name_shorts is not None:
        query = query.filter(models.Project.name_short.in_(name_shorts))
    if name_long is not None:
        query = query.filter(models.Project.name_long == name_long)
    if has_pv_pcs_modules is not None:
        query = query.filter(models.Project.has_pv_pcs_modules == has_pv_pcs_modules)

    return ModelList(query=query, return_query=return_query)


def get_project(
    *, db: Session, project_id: UUID, deep: bool = False, return_query: bool = False
) -> ModelItem[models.Project]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        project_id: TODO: describe.
        deep: TODO: describe.
        return_query: TODO: describe.
    """
    options = get_project_options(deep=deep)
    query: Query = (
        db.query(models.Project)
        .options(options)
        .filter(models.Project.project_id == project_id)
    )
    return ModelItem(query=query, return_query=return_query)


# --- ASYNC SECTION ---
async def get_projects_async(
    *,
    db: AsyncSession,
    deep: bool = False,
    project_ids: list[UUID] | None = None,
    project_type_ids: list[int] | None = None,
    project_status_type_ids: list[enumerations.ProjectStatusType] | None = [
        enumerations.ProjectStatusType.ACTIVE
    ],
    name_short: str | None = None,
    name_shorts: list[str] | None = None,
    name_long: str | None = None,
    has_pv_pcs_modules: bool | None = None,
    return_query: bool = False,
) -> ModelList[models.Project]:
    """
    Retrieve projects from the database as a ModelList.

    Args:
        db (AsyncSession): The database session to use for the query.
        deep (bool, optional): Whether to load related objects. Defaults to False.
        project_ids (list[UUID], optional): Filter by project IDs.
        project_type_ids (list[int], optional): Filter by project type IDs.
        project_status_type_ids (list[ProjectStatusType], optional): Filter by
            project status types. Defaults to ACTIVE only.
        name_short (str, optional): Filter by exact name_short match.
        name_shorts (list[str], optional): Filter by multiple name_short values.
        name_long (str, optional): Filter by exact name_long match.
        has_pv_pcs_modules (bool, optional): Filter by pv_pcs_modules presence.
        return_query (bool, optional): If True, returns ModelList with
            unexecuted query for use with polars_dataframe_async().
            Defaults to False.

    Returns:
        ModelList[models.Project]: A ModelList that can be converted
            to a list of models via .models() or to a polars DataFrame
            via await .polars_dataframe_async().

    Example:
        # Get as list of models
        ml = await get_projects_async(db=db, deep=True)
        projects = ml.models()

        # Get as polars DataFrame
        ml = await get_projects_async(db=db, return_query=True)
        df = await ml.polars_dataframe_async()
    """
    options = get_project_options(deep=deep)

    stmt = select(models.Project).options(options)

    if project_ids is not None:
        stmt = stmt.where(models.Project.project_id.in_(project_ids))
    if project_type_ids is not None:
        stmt = stmt.where(models.Project.project_type_id.in_(project_type_ids))
    if project_status_type_ids is not None:
        status_ids = enumerations.ProjectStatusType.extract_values(
            project_status_type_ids
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

    if return_query:
        # Return ModelList with TextClause for polars execution
        compiled = stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
        text_clause = text(str(compiled))
        return ModelList(query=text_clause)
    else:
        # Execute immediately and return ModelList with items
        result = await db.execute(stmt)
        items = list(result.scalars().all())
        return ModelList.from_items(items)


async def get_project_async(
    *, db: AsyncSession, project_id: UUID, deep: bool = False
) -> models.Project | None:
    """TODO: add description.

    Args:
        db: TODO: describe.
        project_id: TODO: describe.
        deep: TODO: describe.
    """
    options = get_project_options(deep=deep)
    stmt = (
        select(models.Project)
        .options(options)
        .where(models.Project.project_id == project_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_project_id_by_name_short_async(
    *, db: AsyncSession, name_short: str
) -> UUID | None:
    """
    Get project_id by project name_short.

    Args:
        db (AsyncSession): The database session to use for the query.
        name_short (str): The project name_short to look up.

    Returns:
        UUID | None: The project_id if found, None otherwise.
    """
    stmt = select(models.Project.project_id).where(
        models.Project.name_short == name_short
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_project_timezone_and_data_cagg_interval_async(
    *, db: AsyncSession, project_id: UUID
) -> dict[str, str | None] | None:
    """
    Get timezone and data_cagg_interval for a project.

    Args:
        db (AsyncSession): The database session to use for the query.
        project_id (UUID): The project ID to get timezone and data_cagg_interval for.

    Returns:
        dict[str, str | None] | None: A dictionary containing timezone and
            data_cagg_interval, or None if project not found.
    """
    stmt = select(
        models.Project.time_zone,
        models.Project.data_cagg_interval,
    ).where(models.Project.project_id == project_id)

    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        return None

    return {
        "timezone": row.time_zone,
        "data_cagg_interval": row.data_cagg_interval,
    }


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


def update_project_spec(
    *, db: Session, project_id: UUID, spec_updates: dict[str, Any]
) -> models.Project:
    """
    Update the project spec with new values.

    Args:
        db: Database session
        project_id: UUID of the project to update
        spec_updates: Dictionary of spec fields to update

    Returns:
        Updated project model
    """
    project = (
        db.query(models.Project).filter(models.Project.project_id == project_id).first()
    )

    if not project:
        raise ValueError(f"Project with ID {project_id} not found")

    # Get current spec or initialize empty dict
    current_spec = project.spec or {}

    # Update the spec with new values
    updated_spec = {**current_spec, **spec_updates}

    # Update the project's spec field
    project.spec = updated_spec
    db.commit()
    db.refresh(project)

    return project
