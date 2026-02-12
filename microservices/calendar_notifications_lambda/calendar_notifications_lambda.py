"""Lambda handler for calendar notification reminders.

This script is designed to be run as an AWS Lambda function on a schedule.
It checks calendar items with notify_offsets and creates notifications for
events that need reminders sent today.

Schedule: Daily (checks for notifications that should be sent today)
"""

import asyncio
import json
import logging
import os

import boto3
import dotenv
from botocore.exceptions import (  # type: ignore[import-not-found]
    ClientError,
)

# Load environment variables (useful for local runs)
dotenv.load_dotenv()

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
    try:
        client = boto3.client("secretsmanager", region_name=region)
        resp = client.get_secret_value(SecretId=secret_name)
        secret_str = resp.get("SecretString")
        if not secret_str:
            logger.warning(f"Secret {secret_name} has no SecretString")
            return
        data = json.loads(secret_str)
        for key, value in data.items():
            os.environ.setdefault(key, str(value))
        logger.info(f"Successfully loaded secret {secret_name}")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "ResourceNotFoundException":
            logger.warning(
                f"Secret {secret_name} not found in Secrets Manager. "
                f"Continuing without loading secrets."
            )
        else:
            logger.warning(
                f"Error loading secret {secret_name}: {str(e)}. "
                f"Continuing without loading secrets."
            )
    except Exception as e:
        logger.warning(
            f"Error loading secret {secret_name}: {str(e)}. "
            f"Continuing without loading secrets."
        )


# Load secrets BEFORE importing core modules
# (core.settings accesses DATABASE_URL at import time)
# This must happen at module level, not inside a function
def _load_secrets_at_startup() -> None:
    """Load secrets from AWS Secrets Manager before importing core modules."""
    try:
        region = os.getenv("AWS_REGION", "us-east-2")
        load_secret_into_env(
            secret_name="calendar/reminders",  # noqa: S106
            region=region,
        )
    except Exception as e:
        logger.warning(f"Error loading secrets at startup: {str(e)}")


# Load secrets at module import time (before core imports)
_load_secrets_at_startup()


async def _run_calendar_notifications():
    """Run the calendar notifications check in an async context."""
    try:
        # Import here to avoid issues with Lambda environment
        # Secrets are already loaded at module level above
        from core.domain.notifications.calendar_notifications import (  # noqa: PLC0415
            check_calendar_notifications,
        )

        # Determine if running in production based on environment
        api_prod = os.getenv("ENVIRONMENT", "development") == "production"

        logger.info("Starting calendar notifications check")
        summary = await check_calendar_notifications(api_prod=api_prod)
        logger.info(f"Calendar notifications check complete: {summary}")

        return summary

    except Exception as e:
        logger.error(f"Error in calendar notifications lambda: {str(e)}", exc_info=True)
        raise


def lambda_handler(
    event,  # noqa: ARG001
    context,  # noqa: ARG001
):  # nosemgrep: python-enforce-keyword-only-args
    """AWS Lambda handler for calendar notification checks.

    Args:
        event: Lambda event (can be empty dict for scheduled invocations).
        context: Lambda context.

    Returns:
        Dictionary with status code and summary.
    """
    logger.info("LAMBDA_HANDLER_START: Calendar notifications lambda starting")

    try:
        # Use asyncio.run to properly handle the async context
        summary = asyncio.run(_run_calendar_notifications())

        return {
            "statusCode": 200,
            "body": json.dumps(summary),
        }

    except Exception as e:
        logger.error(f"Error in calendar notifications lambda: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }


# For local testing
if __name__ == "__main__":
    # Use the same async approach as the lambda handler
    result = asyncio.run(_run_calendar_notifications())
    logger.info(json.dumps(result, indent=2))
