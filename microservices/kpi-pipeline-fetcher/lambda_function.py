import os

import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

load_dotenv()

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    send_default_pii=True,
    integrations=[AwsLambdaIntegration(timeout_warning=True)],
)


import datetime
from datetime import timedelta
from uuid import UUID

import core.models as models
import pandas as pd
from core.dependencies import with_db
from pydantic import BaseModel, Field
from sqlalchemy import select


class Event(BaseModel):
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
    project_id: UUID
    kpi_type_ids: list[int]


def lambda_handler(event: Event, _context) -> list[str]:
    """Lambda handler for the kpi pipeline fetcher.

    Args:
        event: The event object, an instance of the Event class.
        _context: AWS Lambda context (unused).

    Returns:
        A list of response items.
    """
    event = Event.model_validate(event)
    # by default the start date is the day before the end date

    true_start = event.start - timedelta(days=event.backfill_days)
    if true_start >= event.end:
        return []

    with with_db(schema=None) as db:
        stmt = select(models.KPIInstance)
        if event.project_name_short_list is not None:
            stmt = stmt.join(
                models.Project,
                models.KPIInstance.project_id == models.Project.project_id,
            ).where(models.Project.name_short.in_(event.project_name_short_list))
        if event.kpi_type_ids is not None:
            stmt = stmt.where(models.KPIInstance.kpi_type_id.in_(event.kpi_type_ids))
        kpi_instances = db.execute(stmt).scalars().all()

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
            end=event.end,
            freq=str(event.days_per_chunk) + "D",
            inclusive="left",
        ):
            responses.append(
                ResponseItem(
                    start_date=date.date(),
                    end_date=min(
                        date.date() + timedelta(days=event.days_per_chunk), event.end
                    ),
                    project_id=project_id,
                    kpi_type_ids=list(kpi_type_ids),
                ).model_dump_json()
            )
    return responses
