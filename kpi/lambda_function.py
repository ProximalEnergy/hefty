# Initialize Sentry even before imports

import os

import sentry_sdk
import sentry_sdk.integrations.aws_lambda as sentry_aws_lambda
from dotenv import load_dotenv
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

load_dotenv()
# SDK uses this constant (ms before timeout to fire warning). Default 1500; use 30s.
sentry_aws_lambda.TIMEOUT_WARNING_BUFFER = 30_000
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    send_default_pii=True,
    integrations=[AwsLambdaIntegration(timeout_warning=True)],
)

# now do all of the imports

import datetime
import warnings

from asyncpg.exceptions import ProtocolViolationError  # type: ignore[import-untyped]
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
from pydantic import BaseModel
from sqlalchemy.exc import DBAPIError, OperationalError


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
    )()

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
