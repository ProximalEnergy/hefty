"""Build KPI pipeline work items for Step Functions."""

from __future__ import annotations

import datetime
from datetime import timedelta

import core.models as models
import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session


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


def build_fetcher_response(
    *,
    db: Session,
    event: FetcherLambdaEvent,
) -> list[dict[str, object]]:
    """Build Step Functions map input items for KPI pipeline runs.

    Args:
        db: Database session.
        event: Validated fetcher payload.

    Returns:
        Serialized response items for each project/date chunk.
    """
    true_start = event.start - timedelta(days=event.backfill_days)
    if true_start >= event.end:
        return []

    stmt = select(models.KPIInstance)
    if event.project_name_short_list is not None:
        stmt = stmt.join(
            models.Project,
            models.KPIInstance.project_id == models.Project.project_id,
        ).where(models.Project.name_short.in_(event.project_name_short_list))
    if event.kpi_type_ids is not None:
        stmt = stmt.where(models.KPIInstance.kpi_type_id.in_(event.kpi_type_ids))

    kpi_instances = db.execute(stmt).scalars().all()
    project_names_by_id = {
        project.project_id: project.name_short
        for project in db.execute(select(models.Project)).scalars().all()
    }
    project_ids = {kpi_instance.project_id for kpi_instance in kpi_instances}

    responses: list[dict[str, object]] = []
    for project_id in project_ids:
        kpi_type_ids = {
            kpi_instance.kpi_type_id
            for kpi_instance in kpi_instances
            if kpi_instance.project_id == project_id
        }
        if not kpi_type_ids:
            continue

        for date in pd.date_range(
            start=true_start,
            end=event.end,
            freq=f"{event.days_per_chunk}D",
            inclusive="left",
        ):
            responses.append(
                ResponseItem(
                    start_date=date.date(),
                    end_date=min(
                        date.date() + timedelta(days=event.days_per_chunk),
                        event.end,
                    ),
                    project_name_short=project_names_by_id[project_id],
                    kpi_type_ids=list(kpi_type_ids),
                ).model_dump(mode="json")
            )

    return responses
