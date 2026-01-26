import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
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

metadata = sa.MetaData(
    # Specify default schema
    # NOTE: Changing this value will have downstream effects
    schema="project",
)


# Create a Base class
# This will be the base class for our SQLAlchemy models
class Base(DeclarativeBase):
    metadata = metadata
