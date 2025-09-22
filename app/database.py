from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app import settings

# SYNC
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ASYNC
async_database_url = settings.DATABASE_URL
async_database_url = async_database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)
async_database_url = async_database_url.replace("?sslmode=require", "")
connect_args: dict[str, Any] = {"ssl": True}
async_engine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
    connect_args=connect_args,
)
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
)
