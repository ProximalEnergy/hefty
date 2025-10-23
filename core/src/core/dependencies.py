from collections.abc import AsyncGenerator, AsyncIterator, Generator
from contextlib import asynccontextmanager, contextmanager
from functools import lru_cache
from uuid import UUID

from async_lru import alru_cache
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from core import models
from core.database import async_engine, engine


@contextmanager
def with_db(*, schema: str | None) -> Generator[Session, None, None]:
    """Get a database session with the specified schema."""
    if schema:
        schema_translate_map = dict(project=schema)
    else:
        schema_translate_map = None

    connectable = engine.execution_options(schema_translate_map=schema_translate_map)

    db: Session | None = None
    try:
        db = Session(autocommit=False, autoflush=False, bind=connectable)
        yield db
    finally:
        if db:
            db.close()


@asynccontextmanager
async def with_db_async(*, schema: str | None) -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session with the specified schema."""
    if schema:
        schema_translate_map = dict(project=schema)
    else:
        schema_translate_map = None

    connectable = async_engine.execution_options(
        schema_translate_map=schema_translate_map
    )

    db: AsyncSession | None = None
    try:
        db = AsyncSession(autocommit=False, autoflush=False, bind=connectable)
        yield db
    finally:
        if db:
            await db.close()


def get_db(*, schema: str | None = None) -> Generator[Session, None, None]:
    with with_db(schema=schema) as db:
        yield db


async def get_db_async(
    *, schema: str | None = None
) -> AsyncGenerator[AsyncSession, None]:
    async with with_db_async(schema=schema) as db:
        yield db


def get_db_session(*, schema: str | None = None) -> Session:
    """Get a database session directly (not a generator)."""
    return next(get_db(schema=schema))


@asynccontextmanager
async def get_db_session_async(
    *, schema: str | None = None
) -> AsyncIterator[AsyncSession]:
    """Get an async database session directly (not a generator)."""

    async with with_db_async(schema=schema) as db:
        yield db


@lru_cache(maxsize=128)
def get_project_name_short(*, project_id: UUID) -> str | None:
    with with_db(schema=None) as db:
        project = (
            db.query(models.Project)
            .filter(models.Project.project_id == project_id)
            .first()
        )
    return project.name_short if project else None


@alru_cache(maxsize=128)
async def get_project_name_short_async(*, project_id: UUID) -> str | None:
    async with with_db_async(schema=None) as db:
        stmt = select(models.Project).filter(models.Project.project_id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
    return project.name_short if project else None
