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
from datetime import datetime  # noqa: E402

import boto3  # noqa: E402
from pydantic import BaseModel  # noqa: E402

_DEFAULT_SECRET_NAME = "microservices/cmms_ticket_download"  # noqa: S105


def _load_cmms_ticket_download_secret_into_env() -> None:
    """Load Lambda configuration from AWS Secrets Manager."""
    secret_name = os.getenv("CMMS_TICKET_DOWNLOAD_SECRET_NAME", _DEFAULT_SECRET_NAME)
    region = os.getenv("AWS_REGION", "us-east-2")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    secret_string = response.get("SecretString")
    if not secret_string:
        raise ValueError(f"Secret {secret_name} has no SecretString")

    for key, value in json.loads(secret_string).items():
        os.environ[key] = str(value)


_load_cmms_ticket_download_secret_into_env()

from cmms_ticket_download.cmms import CMMSETL  # noqa: E402


class CMMSTicketDownloadLambdaEvent(BaseModel):
    """Payload for the CMMS ticket download Lambda."""

    cmms_integration_id: int
    start: datetime
    end: datetime


def lambda_handler(event, _context):
    """Run CMMS ticket download ETL for the requested integration.

    Args:
        event: Lambda event payload.
        _context: Lambda runtime context.
    """

    event = CMMSTicketDownloadLambdaEvent(**event)
    cmms_etl = CMMSETL.from_cmms_integration_id(
        cmms_integration_id=event.cmms_integration_id
    )
    result = cmms_etl.run_etl(
        start=event.start,
        end=event.end,
    )

    return {"statusCode": 200, "body": result}
