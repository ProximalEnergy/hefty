"""Lambda handler for weather alert notifications.

This script is designed to be run as an AWS Lambda function on a schedule.
It checks NWS weather forecast polygons and creates notifications for affected projects.

Schedule: Every 30 minutes (aligned with NWS update frequency)
"""

import asyncio
import json
import logging
import os
from importlib import import_module
from typing import Any, cast

import boto3


def _load_local_dotenv() -> None:
    """Load local environment variables when python-dotenv is installed."""
    try:
        dotenv = cast(Any, import_module("dotenv"))
    except ModuleNotFoundError:
        return
    dotenv.load_dotenv()


_load_local_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_secret_into_env(*, secret_name: str, region: str) -> None:
    """Load a JSON secret into environment variables.

    Args:
        secret_name: Name of the AWS Secrets Manager secret.
        region: AWS region where the secret is stored.
    """
    client = boto3.client("secretsmanager", region_name=region)
    resp = client.get_secret_value(SecretId=secret_name)
    secret_str = resp.get("SecretString")
    if not secret_str:
        return
    data = json.loads(secret_str)
    for key, value in data.items():
        os.environ.setdefault(key, str(value))


async def _run_weather_alerts():
    """Run the weather alerts check in an async context."""
    try:
        # Load secrets first (if configured)
        secret_name = os.getenv("NWS_SECRET_NAME", "nws/weather/notifications")
        region = os.getenv("AWS_REGION", "us-east-2")
        load_secret_into_env(secret_name=secret_name, region=region)

        # Import here to avoid issues with Lambda environment
        from core.domain.notifications.weather_alerts import (  # noqa: PLC0415
            check_weather_alerts,
        )

        # Determine if running in production based on environment
        api_prod = os.getenv("ENVIRONMENT", "development") == "production"

        logger.info("Starting weather alert check")
        summary = await check_weather_alerts(api_prod=api_prod)
        logger.info(f"Weather alert check complete: {summary}")

        return summary

    except Exception as e:
        logger.error(f"Error in weather alerts lambda: {str(e)}", exc_info=True)
        raise


def lambda_handler(
    event,  # noqa: ARG001
    context,  # noqa: ARG001
):  # nosemgrep: python-enforce-keyword-only-args
    """AWS Lambda handler for weather alert checks.

    Args:
        event: Lambda event (can be empty dict for scheduled invocations).
        context: Lambda context.

    Returns:
        Dictionary with status code and summary.
    """
    logger.info("LAMBDA_HANDLER_START: Weather alerts lambda starting")

    try:
        # Use asyncio.run to properly handle the async context
        summary = asyncio.run(_run_weather_alerts())

        return {
            "statusCode": 200,
            "body": json.dumps(summary),
        }

    except Exception as e:
        logger.error(f"Error in weather alerts lambda: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }


# For local testing
if __name__ == "__main__":
    # Use the same async approach as the lambda handler
    result = asyncio.run(_run_weather_alerts())
    logger.info(json.dumps(result, indent=2))
