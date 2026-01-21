import os

from dotenv import load_dotenv

from app._utils.aws import get_parameters_by_path
from app.logger import logger

# Load environment variables once at module import
load_dotenv(override=True)


_PARAMETER_STORE_SENTINEL = "_PARAMETER_STORE_LOADED"


def _populate_env_from_parameter_store() -> None:
    """Handle  populate env from parameter store."""
    if os.environ.get(_PARAMETER_STORE_SENTINEL) == "1":
        return

    # Allow deployments to opt out entirely.
    if os.getenv("DISABLE_PARAMETER_STORE_BOOTSTRAP", "").lower() in {
        "1",
        "true",
        "yes",
    }:
        return

    parameter_path = os.getenv("AWS_PARAMETER_STORE_PATH", "/proximal/api/")
    if not parameter_path:
        return

    region = (
        os.getenv("AWS_PARAMETER_STORE_REGION")
        or os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or "us-east-2"
    )

    try:
        parameters = get_parameters_by_path(
            path=parameter_path,
            region_name=region,
            recursive=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Unable to load parameters from SSM path '%s': %s",
            parameter_path,
            exc,
        )
        return

    for key, value in parameters.items():
        os.environ.setdefault(key, value)

    os.environ[_PARAMETER_STORE_SENTINEL] = "1"


_populate_env_from_parameter_store()

# Environment settings
ENVIRONMENT = os.getenv("ENVIRONMENT")

# Database settings
DATABASE_URL = os.environ["DATABASE_URL"]
CONNECTION_STRING = os.getenv("CONNECTION_STRING")

# Authentication settings
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_SECRET_KEY_DEVELOPMENT = os.getenv("CLERK_SECRET_KEY_DEVELOPMENT")
URL_JWKS = os.getenv("URL_JWKS")
URL_JWKS_DEVELOPMENT = os.getenv("URL_JWKS_DEVELOPMENT")

# Google Sheets settings
COMMISSIONING_KEY_JSON = os.getenv("COMMISSIONING_KEY_JSON")

# AWS settings
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")

# Weather API settings
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# File paths
EXCEL_PATH = os.getenv("EXCEL_PATH")

# Tenaska token manager
TENASKA_TOKEN_URL = os.getenv("TENASKA_TOKEN_URL")
TENASKA_CLIENT_ID = os.getenv("TENASKA_CLIENT_ID")
TENASKA_CLIENT_SECRET = os.getenv("TENASKA_CLIENT_SECRET")

# aws lambda
LAMBDA_ARN_KPI_PIPELINE = os.getenv("LAMBDA_ARN_KPI_PIPELINE")

VERSION = 3

# ClickHouse Settings
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST")
CLICKHOUSE_USERNAME = os.getenv("CLICKHOUSE_USER")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD")
CLICKHOUSE_PORT = 8443
