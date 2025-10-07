from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, noload, selectinload

from core import models
from core.model_list import ModelItem, ModelList


def _get_project_tag_options(*, deep: bool) -> Any:
    if deep:
        options = (
            selectinload(models.Tag.device),
            selectinload(models.Tag.sensor_type),
            selectinload(models.Tag.data_type),
        )
    else:
        options = (
            noload(models.Tag.device),
            noload(models.Tag.sensor_type),
            noload(models.Tag.data_type),
        )

    return options


def get_project_tag(
    db: Session, tag_id: int, *, deep: bool, return_query: bool = False
) -> ModelItem[models.Tag]:
    options = _get_project_tag_options(deep=deep)
    query = db.query(models.Tag).options(*options).filter(models.Tag.tag_id == tag_id)
    return ModelItem(query=query, return_query=return_query)


def get_project_tags(
    db: Session,
    *,
    tag_ids: list[int] = [],
    in_tsdb: bool | None = None,
    device_ids: list[int] = [],
    sensor_type_ids: list[int] = [],
    sensor_type_name_shorts: list[str] = [],
    data_type_ids: list[int] = [],
    name_short: str = "",
    name_long: str = "",
    name_scada: str = "",
    deep: bool = False,
    include_ghost_tags: bool = False,
    has_sensor_type_id: bool = False,
    return_query: bool = False,
) -> ModelList[models.Tag]:
    options = _get_project_tag_options(deep=deep)

    query = db.query(models.Tag).options(*options)

    if tag_ids:
        query = query.filter(models.Tag.tag_id.in_(tag_ids))
    if in_tsdb is not None:
        query = query.filter(models.Tag.in_tsdb == in_tsdb)
    if device_ids:
        query = query.filter(models.Tag.device_id.in_(device_ids))
    if sensor_type_ids:
        query = query.filter(models.Tag.sensor_type_id.in_(sensor_type_ids))
    if sensor_type_name_shorts:
        query = query.filter(
            models.Tag.sensor_type.has(
                models.SensorType.name_short.in_(sensor_type_name_shorts),
            ),
        )
    if data_type_ids:
        query = query.filter(models.Tag.data_type_id.in_(data_type_ids))
    if name_short:
        query = query.filter(models.Tag.name_short == name_short)
    if name_long:
        query = query.filter(models.Tag.name_long == name_long)
    if name_scada:
        query = query.filter(models.Tag.name_scada == name_scada)
    if has_sensor_type_id:
        query = query.filter(models.Tag.sensor_type_id != None)  # noqa: E711
    if not include_ghost_tags:
        query = query.filter(models.Tag.device_id != 0)
        query = query.filter(models.Tag.sensor_type_id != 0)
    return ModelList(query=query, return_query=return_query)


# --- ASYNC SECTION ---
async def get_project_tag_async(
    db: AsyncSession, tag_id: int, *, deep: bool
) -> models.Tag | None:
    options = _get_project_tag_options(deep=deep)
    stmt = select(models.Tag).options(*options).where(models.Tag.tag_id == tag_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_project_tags_async(
    db: AsyncSession,
    *,
    tag_ids: list[int] = [],
    in_tsdb: bool | None = None,
    device_ids: list[int] = [],
    sensor_type_ids: list[int] = [],
    sensor_type_name_shorts: list[str] = [],
    data_type_ids: list[int] = [],
    name_short: str = "",
    name_long: str = "",
    name_scada: str = "",
    deep: bool = False,
    include_ghost_tags: bool = False,
    has_sensor_type_id: bool = False,
) -> list[models.Tag]:
    options = _get_project_tag_options(deep=deep)

    stmt = select(models.Tag).options(*options)

    if tag_ids:
        stmt = stmt.where(models.Tag.tag_id.in_(tag_ids))
    if in_tsdb is not None:
        stmt = stmt.where(models.Tag.in_tsdb == in_tsdb)
    if device_ids:
        stmt = stmt.where(models.Tag.device_id.in_(device_ids))
    if sensor_type_ids:
        stmt = stmt.where(models.Tag.sensor_type_id.in_(sensor_type_ids))
    if sensor_type_name_shorts:
        stmt = stmt.where(
            models.Tag.sensor_type.has(
                models.SensorType.name_short.in_(sensor_type_name_shorts),
            ),
        )
    if data_type_ids:
        stmt = stmt.where(models.Tag.data_type_id.in_(data_type_ids))
    if name_short:
        stmt = stmt.where(models.Tag.name_short == name_short)
    if name_long:
        stmt = stmt.where(models.Tag.name_long == name_long)
    if name_scada:
        stmt = stmt.where(models.Tag.name_scada == name_scada)
    if not include_ghost_tags:
        stmt = stmt.where(models.Tag.device_id != 0)
        stmt = stmt.where(models.Tag.sensor_type_id != 0)
    if has_sensor_type_id:
        stmt = stmt.where(models.Tag.sensor_type_id != None)  # noqa: E711

    result = await db.execute(stmt)
    return list(result.scalars().all())
