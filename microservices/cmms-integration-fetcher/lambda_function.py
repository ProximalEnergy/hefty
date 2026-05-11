import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

SENTRY_DSN = "https://e505db16112c738a188429c5e0590de6@o4506555874672640.ingest.us.sentry.io/4510874280787968"

sentry_sdk.init(
    dsn=SENTRY_DSN,
    send_default_pii=True,
    integrations=[AwsLambdaIntegration(timeout_warning=True)],
)

import json  # noqa: E402
import os  # noqa: E402
from datetime import date, timedelta  # noqa: E402
from typing import Any  # noqa: E402

import boto3  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from sqlalchemy import select  # noqa: E402

_DEFAULT_SECRET_NAME = "microservices/cmms_integration_fetcher"  # noqa: S105


def _load_cmms_integration_fetcher_secret_into_env() -> None:
    """Load Lambda configuration from AWS Secrets Manager."""
    secret_name = os.getenv(
        "CMMS_INTEGRATION_FETCHER_SECRET_NAME", _DEFAULT_SECRET_NAME
    )
    region = os.getenv("AWS_REGION", "us-east-2")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    secret_string = response.get("SecretString")
    if not secret_string:
        raise ValueError(f"Secret {secret_name} has no SecretString")

    for key, value in json.loads(secret_string).items():
        os.environ[key] = str(value)


_load_cmms_integration_fetcher_secret_into_env()

from core.db_query import DbQuery, OutputType  # noqa: E402

from core import models  # noqa: E402


class CMMSIntegrationFetcherEvent(BaseModel):
    """Payload for selecting CMMS integrations to fetch."""

    start: date = Field(default_factory=date.today)
    end: date = Field(default_factory=date.today)
    backfill_days: int = 0
    cmms_integration_ids: list[int] | None = None


class CMMSIntegrationFetcherResponseItem(BaseModel):
    """A single CMMS integration fetch request."""

    cmms_integration_id: int
    start: date
    end: date


def lambda_handler(event, _context) -> list[dict[str, Any]]:
    """Build fetch requests for each matching CMMS integration.

    Args:
        event: Lambda event payload.
        _context: Lambda runtime context.
    """

    event = CMMSIntegrationFetcherEvent(**event)
    # calculate start including backfill days
    true_start = event.start - timedelta(days=event.backfill_days)
    stmt = select(
        models.CMMSIntegration.cmms_integration_id,
    )
    # filter by cmms_integration_ids if not None
    if event.cmms_integration_ids is not None:
        stmt = stmt.where(
            models.CMMSIntegration.cmms_integration_id.in_(event.cmms_integration_ids)
        )

    query = DbQuery(query=stmt)
    response = query.get(output_type=OutputType.SQLALCHEMY)

    result = [
        CMMSIntegrationFetcherResponseItem(
            cmms_integration_id=cmms_integration_id,
            start=true_start,
            end=event.end,
        ).model_dump(mode="json")
        for cmms_integration_id in response
    ]
    return result
