from collections.abc import AsyncGenerator, AsyncIterator, Generator
from contextlib import asynccontextmanager, contextmanager
from functools import lru_cache
from uuid import UUID

from async_lru import alru_cache
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Session

from core import models
from core.database import async_engine, engine


@contextmanager
def with_db(
    *,
    schema: str | None = "operational",
) -> Generator[Session, None, None]:
    """Get a database session with the specified schema.

    Args:
        schema: Schema name to bind for schema translation.
    """
    # Only set schema_translate_map when schema is provided.
    # Passing schema_translate_map=None still enables translation mode
    # and generates __[SCHEMA_x]__ placeholders that won't resolve.
    connectable: Engine = (
        engine.execution_options(schema_translate_map={"project": schema})
        if schema
        else engine
    )

    db: Session | None = None
    try:
        db = Session(autocommit=False, autoflush=False, bind=connectable)
        yield db
    finally:
        if db:
            db.close()


@asynccontextmanager
async def with_db_async(
    *,
    schema: str | None = "operational",
) -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session with the specified schema.

    Args:
        schema: Schema name to bind for schema translation.
    """
    # Only set schema_translate_map when schema is provided.
    # Passing schema_translate_map=None still enables translation mode
    # and generates __[SCHEMA_x]__ placeholders that won't resolve.
    connectable: AsyncEngine = (
        async_engine.execution_options(schema_translate_map={"project": schema})
        if schema
        else async_engine
    )

    db: AsyncSession | None = None
    try:
        db = AsyncSession(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            bind=connectable,
        )
        yield db
    finally:
        if db:
            await db.close()


def get_db(
    *,
    schema: str | None = "operational",
) -> Generator[Session, None, None]:
    """Yield a database session scoped to the requested schema.

    Args:
        schema: Schema name to bind for schema translation.
    """
    with with_db(schema=schema) as db:
        yield db


async def get_db_async(
    *,
    schema: str | None = "operational",
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session scoped to the requested schema.

    Args:
        schema: Schema name to bind for schema translation.
    """
    async with with_db_async(schema=schema) as db:
        yield db


def get_db_session(
    *,
    schema: str | None = "operational",
) -> Session:
    """Get a database session directly (not a generator).

    Args:
        schema: Schema name to bind for schema translation.
    """
    return next(get_db(schema=schema))


@asynccontextmanager
async def get_db_session_async(
    *,
    schema: str | None = "operational",
) -> AsyncIterator[AsyncSession]:
    """Get an async database session directly (not a generator).

    Args:
        schema: Schema name to bind for schema translation.
    """

    async with with_db_async(schema=schema) as db:
        yield db


@lru_cache(maxsize=128)
def get_project_name_short(*, project_id: UUID) -> str | None:
    """Lookup a project's short name by project id.

    Args:
        project_id: UUID of the project to look up.
    """
    with with_db(schema=None) as db:
        stmt = select(models.Project.name_short).where(
            models.Project.project_id == project_id
        )
        result = db.execute(stmt)
        return result.scalar_one_or_none()


@alru_cache(maxsize=128)
async def get_project_name_short_async(*, project_id: UUID) -> str | None:
    """Lookup a project's short name asynchronously by project id.

    Args:
        project_id: UUID of the project to look up.
    """
    async with with_db_async(schema=None) as db:
        stmt = select(models.Project).where(models.Project.project_id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
    return project.name_short if project else None
