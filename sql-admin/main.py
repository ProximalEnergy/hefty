"""Main Starlette Admin app using core models and database."""

import logging
import os
import sys
from contextlib import asynccontextmanager

from core.settings import DATABASE_URL, ENVIRONMENT
from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy import create_engine
from starlette_admin.contrib.sqla import Admin

from admin_views import setup_admin_views

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def get_schema_to_use() -> str:
    """Resolve the target schema for either `python main.py` or uvicorn."""
    if schema := os.getenv("SQL_ADMIN_SCHEMA"):
        return schema
    if len(sys.argv) > 1:
        cli_arg = sys.argv[1]
        if ":" not in cli_arg and not cli_arg.startswith("-"):
            return cli_arg
    return "project_default"


SCHEMA_TO_USE = get_schema_to_use()

# Configuration
APP_TITLE = f"Starlette Admin ({SCHEMA_TO_USE})"
APP_VERSION = "1.0.0"
DEBUG = ENVIRONMENT != "production"


logger.info("Using database URL: %s", DATABASE_URL)
logger.info("Environment: %s", ENVIRONMENT)

# Create SQLAlchemy engine with schema translation for target project
engine = create_engine(
    DATABASE_URL, execution_options={"schema_translate_map": {"project": SCHEMA_TO_USE}}
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Args:
        app: FastAPI application instance.
    """
    # Startup
    logger.info("Starlette Admin application starting...")
    logger.info("Using existing core database connection")

    yield

    # Shutdown
    logger.info("Starlette Admin application shutting down...")


# Create FastAPI app
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    debug=DEBUG,
    lifespan=lifespan,
)

# Create Starlette Admin instance using core database engine
admin = Admin(engine=engine, title=APP_TITLE)

# Set up admin views for core models
setup_admin_views(admin=admin)
admin.mount_to(app)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Proximal Energy Starlette Admin",
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "admin_url": "/admin",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8001,  # Use different port to avoid conflict with main API
        reload=DEBUG,
    )
