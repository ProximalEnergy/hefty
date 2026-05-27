# Initialize Sentry even before imports


import sentry_sdk
import sentry_sdk.integrations.aws_lambda as sentry_aws_lambda
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

SENTRY_DSN = "https://11a4bd8327572edf71196106139c0298@o4506555874672640.ingest.us.sentry.io/4510524365799424"


# SDK uses this constant (ms before timeout to fire warning). Default 1500; use 30s.
sentry_aws_lambda.TIMEOUT_WARNING_BUFFER = 30_000
sentry_sdk.init(
    dsn=SENTRY_DSN,
    send_default_pii=True,
    integrations=[AwsLambdaIntegration(timeout_warning=True)],
)

# now do all of the imports

import datetime
import json
import os
import warnings

import boto3
from asyncpg.exceptions import ProtocolViolationError  # type: ignore[import-untyped]
from pydantic import BaseModel
from sqlalchemy.exc import DBAPIError, OperationalError

_KPI_SECRET_NAME = "kpi"  # noqa: S105


def _load_kpi_secret_into_env() -> None:
    """Load Lambda configuration from AWS Secrets Manager."""
    region = os.getenv("AWS_REGION", "us-east-2")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=_KPI_SECRET_NAME)
    secret_string = response.get("SecretString")
    if not secret_string:
        raise ValueError(f"Secret {_KPI_SECRET_NAME} has no SecretString")

    for key, value in json.loads(secret_string).items():
        os.environ[key] = str(value)


_load_kpi_secret_into_env()

from core.enumerations import KPITypeEnum, ProjectID
from kpi.base.exception import (
    DatasetAccessError,
    MissingDataError,
    NoDownloadedDataError,
    ValidationError,
)
from kpi.base.warning import UnimplementedWarning
from kpi.op.create import create_dataset
from kpi.op.observer import SentryObserver, observe, set_global_observer
from kpi.op.plan import get_plan
from kpi.registry.upload.api import UPLOAD
from kpi.schema.api import get_pipeline


class KpiLambdaEvent(BaseModel):
    """Lambda payload."""

    start_date: datetime.date
    end_date: datetime.date
    project_name_short: str
    kpi_type_ids: list[int]


set_global_observer(
    SentryObserver(
        # there are a lot of sentry warnings right now,
        # so I will ignore the validation warnings for now
        # and turn this on later
        capture_warnings=(),
        ignore_errors=(
            DatasetAccessError,
            MissingDataError,
            NoDownloadedDataError,
            ValidationError,
            ProtocolViolationError,
            DBAPIError,
            OperationalError,
        ),
    )
)


def lambda_handler(event, _context):
    """Lambda handler."""
    sentry_sdk.set_context("lambda_payload", event)
    event = KpiLambdaEvent.model_validate(event)

    project_id = ProjectID[event.project_name_short.upper()].value

    pipeline = get_pipeline(
        project_id=project_id,
    )

    with observe():
        output_kpis: set[str] = set()
        for kpi_type_id in event.kpi_type_ids:
            if kpi_type_id in KPITypeEnum:
                output_kpis.add(KPITypeEnum(kpi_type_id).name)
                continue
            warnings.warn(
                f"Ignoring unknown KPI type id in lambda payload: {kpi_type_id}",
                UnimplementedWarning,
            )

        implemented_kpis = UPLOAD.keys()
        unimplemented_kpis = output_kpis.difference(implemented_kpis)
        if unimplemented_kpis:
            warnings.warn(
                f"Unimplemented KPIs in lambda payload: {unimplemented_kpis}",
                UnimplementedWarning,
            )
    output_kpis = output_kpis.intersection(implemented_kpis)

    plan = get_plan(schema=pipeline, outputs=output_kpis)

    dataset = create_dataset(
        project_id=project_id,
        start_date=event.start_date,
        end_date=event.end_date,
    )

    pipeline.run(dataset=dataset, plan=plan)

    return {"statusCode": 200, "body": "Success"}
