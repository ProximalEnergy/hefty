"""Centralized settings and environment variable management for the core application."""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
# This should be done once at application startup
load_dotenv(override=True)


def get_database_url() -> str:
    """Get the database URL from environment variables.

    Returns:
        str: The database URL

    Raises:
        ValueError: If DATABASE_URL is not set
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url is None:
        raise ValueError("DATABASE_URL is not set")
    return database_url


def get_environment() -> str | None:
    """Get the current environment from environment variables.

    Returns:
        str | None: The environment name, or None if not set
    """
    return os.getenv("ENVIRONMENT")


def get_clerk_secret_key() -> str | None:
    """Get the Clerk secret key from environment variables.

    Returns:
        str | None: The Clerk secret key, or None if not set
    """
    return os.getenv("CLERK_SECRET_KEY")


# Pre-compute commonly used settings
DATABASE_URL = get_database_url()
ENVIRONMENT = get_environment()
