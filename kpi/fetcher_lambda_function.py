"""Lambda entrypoint for KPI pipeline fetcher."""

from __future__ import annotations

import json
import os
from typing import Any

import boto3
import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

SENTRY_DSN = (
    "https://11a4bd8327572edf71196106139c0298"
    "@o4506555874672640.ingest.us.sentry.io/4510524365799424"
)

sentry_sdk.init(
    dsn=SENTRY_DSN,
    send_default_pii=True,
    integrations=[AwsLambdaIntegration(timeout_warning=True)],
)

_KPI_SECRET_NAME = "kpi"  # noqa: S105


def _load_fetcher_kpi_secret_into_env() -> None:
    """Load Lambda configuration from AWS Secrets Manager."""
    region = os.getenv("AWS_REGION", "us-east-2")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=_KPI_SECRET_NAME)
    secret_string = response.get("SecretString")
    if not secret_string:
        raise ValueError(f"Secret {_KPI_SECRET_NAME} has no SecretString")

    for key, value in json.loads(secret_string).items():
        os.environ[key] = str(value)


_load_fetcher_kpi_secret_into_env()

from core.database import with_db  # noqa: E402
from kpi.infra.fetcher import FetcherLambdaEvent, build_fetcher_response  # noqa: E402


def lambda_handler(event: dict[str, Any], _context: Any) -> list[dict[str, object]]:
    """Lambda handler for the KPI pipeline fetcher.

    Args:
        event: The raw Lambda payload to validate into FetcherLambdaEvent.
        _context: AWS Lambda context.

    Returns:
        A list of response items.
    """
    validated_event = FetcherLambdaEvent.model_validate(event)
    with with_db(schema=None) as db:
        return build_fetcher_response(db=db, event=validated_event)
