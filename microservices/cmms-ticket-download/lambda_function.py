import os

import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

load_dotenv()

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    # Add data like request headers and IP for users,
    # see Sentry data management docs for more info
    send_default_pii=True,
    integrations=[AwsLambdaIntegration(timeout_warning=True)],
)

from datetime import datetime

from cmms_ticket_download.cmms import CMMSETL
from pydantic import BaseModel


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
