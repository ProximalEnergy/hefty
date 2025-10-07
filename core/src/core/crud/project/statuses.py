from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from core import models
from core.model_list import ModelList


def get_status_lookup(
    db: Session,
    *,
    status_lookup_ids: list[int] = [],
    return_query: bool = False,
) -> ModelList[models.StatusLookup]:
    query = db.query(models.StatusLookup)
    if status_lookup_ids:
        query = query.filter(
            models.StatusLookup.status_lookup_id.in_(status_lookup_ids),
        )
    return ModelList(query=query, return_query=return_query)


def get_status_binary(
    db: Session,
    *,
    status_binary_ids: list[int] = [],
    return_query: bool = False,
) -> ModelList[models.StatusBinary]:
    query = db.query(models.StatusBinary)
    if status_binary_ids:
        query = query.filter(
            models.StatusBinary.status_binary_id.in_(status_binary_ids),
        )
    return ModelList(query=query, return_query=return_query)


def get_status_boolean(
    db: Session,
    *,
    status_boolean_ids: list[int] = [],
    return_query: bool = False,
) -> ModelList[models.StatusBoolean]:
    query = db.query(models.StatusBoolean)
    if status_boolean_ids:
        query = query.filter(
            models.StatusBoolean.status_boolean_id.in_(status_boolean_ids),
        )
    return ModelList(query=query, return_query=return_query)


def get_status_string(
    db: Session,
    *,
    status_string_ids: list[int] = [],
    return_query: bool = False,
) -> ModelList[models.StatusString]:
    query = db.query(models.StatusString)
    if status_string_ids:
        query = query.filter(
            models.StatusString.status_string_id.in_(status_string_ids),
        )
    return ModelList(query=query, return_query=return_query)


# --- ASYNC SECTION ---
async def get_status_lookup_async(
    db: AsyncSession,
    *,
    status_lookup_ids: list[int] = [],
) -> list[models.StatusLookup]:
    stmt = select(models.StatusLookup)
    if status_lookup_ids:
        stmt = stmt.where(
            models.StatusLookup.status_lookup_id.in_(status_lookup_ids),
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_status_binary_async(
    db: AsyncSession,
    *,
    status_binary_ids: list[int] = [],
) -> list[models.StatusBinary]:
    stmt = select(models.StatusBinary)
    if status_binary_ids:
        stmt = stmt.where(
            models.StatusBinary.status_binary_id.in_(status_binary_ids),
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_status_boolean_async(
    db: AsyncSession,
    *,
    status_boolean_ids: list[int] = [],
) -> list[models.StatusBoolean]:
    stmt = select(models.StatusBoolean)
    if status_boolean_ids:
        stmt = stmt.where(
            models.StatusBoolean.status_boolean_id.in_(status_boolean_ids),
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_status_string_async(
    db: AsyncSession,
    *,
    status_string_ids: list[int] = [],
) -> list[models.StatusString]:
    stmt = select(models.StatusString)
    if status_string_ids:
        stmt = stmt.where(
            models.StatusString.status_string_id.in_(status_string_ids),
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())
