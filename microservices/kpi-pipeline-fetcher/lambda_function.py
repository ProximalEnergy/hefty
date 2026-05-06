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

import datetime  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
from datetime import timedelta  # noqa: E402
from typing import Any  # noqa: E402

import boto3  # noqa: E402
import pandas as pd  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from sqlalchemy import select  # noqa: PLC0415

_DEFAULT_SECRET_NAME = "microservices/kpi_pipeline_fetcher"  # noqa: S105


def _load_kpi_pipeline_fetcher_secret_into_env() -> None:
    """Load Lambda configuration from AWS Secrets Manager."""
    secret_name = os.getenv("KPI_PIPELINE_FETCHER_SECRET_NAME", _DEFAULT_SECRET_NAME)
    region = os.getenv("AWS_REGION", "us-east-2")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    secret_string = response.get("SecretString")
    if not secret_string:
        raise ValueError(f"Secret {secret_name} has no SecretString")

    for key, value in json.loads(secret_string).items():
        os.environ[key] = str(value)


_load_kpi_pipeline_fetcher_secret_into_env()

import core.models as models  # noqa: PLC0415
from core.dependencies import with_db  # noqa: PLC0415


class FetcherLambdaEvent(BaseModel):
    """Lambda invocation payload: date range and optional filters."""

    start: datetime.date = Field(default_factory=datetime.date.today)
    end: datetime.date = Field(default_factory=datetime.date.today)
    backfill_days: int = 0
    days_per_chunk: int = 1
    project_name_short_list: list[str] | None = None
    kpi_type_ids: list[int] | None = None


class ResponseItem(BaseModel):
    """Serialized chunk descriptor for the KPI pipeline."""

    start_date: datetime.date
    end_date: datetime.date
    project_name_short: str
    kpi_type_ids: list[int]


def lambda_handler(event: dict[str, Any], _context) -> list[str]:
    """Lambda handler for the kpi pipeline fetcher.

    Args:
        event: The raw Lambda payload to validate into FetcherLambdaEvent.
        _context: AWS Lambda context (unused).

    Returns:
        A list of response items.
    """

    validated_event = FetcherLambdaEvent.model_validate(event)
    # by default the start date is the day before the end date

    true_start = validated_event.start - timedelta(days=validated_event.backfill_days)
    if true_start >= validated_event.end:
        return []

    with with_db(schema=None) as db:
        stmt = select(models.KPIInstance)
        if validated_event.project_name_short_list is not None:
            stmt = stmt.join(
                models.Project,
                models.KPIInstance.project_id == models.Project.project_id,
            ).where(
                models.Project.name_short.in_(validated_event.project_name_short_list)
            )
        if validated_event.kpi_type_ids is not None:
            stmt = stmt.where(
                models.KPIInstance.kpi_type_id.in_(validated_event.kpi_type_ids)
            )
        kpi_instances = db.execute(stmt).scalars().all()
        project_names_by_id = {
            project.project_id: project.name_short
            for project in db.execute(select(models.Project)).scalars().all()
        }

    project_ids = {kpi_instance.project_id for kpi_instance in kpi_instances}

    responses = []

    for project_id in project_ids:
        kpi_type_ids = {
            kpi_instance.kpi_type_id
            for kpi_instance in kpi_instances
            if kpi_instance.project_id == project_id
        }
        if len(kpi_type_ids) == 0:
            continue

        for date in pd.date_range(
            start=true_start,
            end=validated_event.end,
            freq=str(validated_event.days_per_chunk) + "D",
            inclusive="left",
        ):
            responses.append(
                ResponseItem(
                    start_date=date.date(),
                    end_date=min(
                        date.date() + timedelta(days=validated_event.days_per_chunk),
                        validated_event.end,
                    ),
                    project_name_short=project_names_by_id[project_id],
                    kpi_type_ids=list(kpi_type_ids),
                ).model_dump_json()
            )
    return responses
