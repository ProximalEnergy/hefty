"""Main SQLAdmin application using core models and database."""

import logging
import os
import sys
from contextlib import asynccontextmanager

from core.settings import DATABASE_URL, ENVIRONMENT
from dotenv import load_dotenv
from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy import create_engine

from admin_views import setup_admin_views

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Determine schema to use
SCHEMA_TO_USE = os.getenv("SQL_ADMIN_SCHEMA")
if not SCHEMA_TO_USE:
    if len(sys.argv) > 1:
        SCHEMA_TO_USE = sys.argv[1]
    else:
        SCHEMA_TO_USE = "project_default"

# Configuration
APP_TITLE = f"SQLAdmin ({SCHEMA_TO_USE})"
APP_VERSION = "1.0.0"
DEBUG = ENVIRONMENT != "production"


logger.info("Using database URL: %s", DATABASE_URL)
logger.info("Environment: %s", ENVIRONMENT)

# Create our own engine for SQLAdmin (avoiding async engine issues)
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
    logger.info("SQLAdmin application starting...")
    logger.info("Using existing core database connection")

    yield

    # Shutdown
    logger.info("SQLAdmin application shutting down...")


# Create FastAPI app
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    debug=DEBUG,
    lifespan=lifespan,
)

# Create SQLAdmin instance using core database engine
admin = Admin(app, engine, title=APP_TITLE)

# Set up admin views for core models
setup_admin_views(admin)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Proximal Energy SQLAdmin",
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
