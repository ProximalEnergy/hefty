from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import NullPool

from core.settings import DATABASE_URL, ENVIRONMENT, get_database_url


def database_url() -> str:
    """Get the database URL from environment variables.

    This function is kept for backwards compatibility.
    New code should import DATABASE_URL directly from settings.
    """
    return get_database_url()


# Create SQLAlchemy engine
# For more information about choosing NullPool, see below.
# https://pablomarti.dev/sqlalchemy-pgbouncer/
# https://dba.stackexchange.com/questions/36828/how-to-best-use-connection-pooling-in-sqlalchemy-for-pgbouncer-transaction-level
# https://github.com/sqlalchemy/sqlalchemy/discussions/8386#discussioncomment-3393023
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args={
        "application_name": f"API ({ENVIRONMENT})",
    },
)

# Create async SQLAlchemy engine
async_database_url = DATABASE_URL
async_database_url = async_database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)
async_database_url = async_database_url.replace("?sslmode=require", "")
connect_args = {"ssl": True}

async_engine = create_async_engine(
    async_database_url,
    poolclass=NullPool,
    pool_pre_ping=True,
    connect_args=connect_args,
)


AsyncSessionLambda = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=async_engine,
)

# Postgres-aligned constraint names for Alembic autogenerate (PRO-1820).
NAMING_CONVENTION = {
    "pk": "%(table_name)s_pkey",
    "fk": "%(table_name)s_%(column_0_N_name)s_fkey",
    "uq": "%(table_name)s_%(column_0_N_name)s_key",
    "ix": "ix_%(column_0_label)s",
}

metadata = sa.MetaData(
    # Specify default schema
    # NOTE: Changing this value will have downstream effects
    schema="project",
    naming_convention=NAMING_CONVENTION,
)


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


# Create a Base class
# This will be the base class for our SQLAlchemy models
class Base(DeclarativeBase):
    metadata = metadata
