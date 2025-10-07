from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, noload, selectinload
from sqlalchemy.orm.query import Query
from sqlalchemy.orm.strategy_options import _AbstractLoad

from core import enumerations, models
from core.model_list import ModelItem, ModelList


def get_project_options(*, deep: bool) -> _AbstractLoad:
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
    options = get_project_options(deep=deep)
    query: Query = (
        db.query(models.Project)
        .options(options)
        .filter(models.Project.project_id == project_id)
    )
    return ModelItem(query=query, return_query=return_query)


# --- ASYNC SECTION ---
async def get_projects_async(
    db: AsyncSession,
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
) -> list[models.Project]:
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

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_project_async(
    *, db: AsyncSession, project_id: UUID, deep: bool = False
) -> models.Project | None:
    options = get_project_options(deep=deep)
    stmt = (
        select(models.Project)
        .options(options)
        .where(models.Project.project_id == project_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
