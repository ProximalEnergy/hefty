from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from core import models
from core.model_list import ModelList


def get_event_losses(
    db: Session,
    *,
    time_equals: datetime.datetime | None = None,
    time_gte: datetime.datetime | None = None,
    time_lt: datetime.datetime | None = None,
    event_ids: list | None = None,
    return_query: bool = False,
) -> ModelList[models.EventLoss]:
    query = db.query(models.EventLoss)
    if time_equals is not None:
        query = query.filter(models.EventLoss.time == time_equals)
    if time_gte is not None:
        query = query.filter(models.EventLoss.time >= time_gte)
    if time_lt is not None:
        query = query.filter(models.EventLoss.time < time_lt)
    if event_ids is not None:
        query = query.filter(models.EventLoss.event_id.in_(event_ids))
    return ModelList(query=query, return_query=return_query)


def get_event_losses_summary_in_sql(
    db: Session,
    *,
    project_name: str,
    event_ids: list[int],
) -> Sequence[Row[Any]]:
    # Early return for empty list to avoid IN ()
    if not event_ids:
        return []

    metadata = sa.MetaData()
    event_losses_table = sa.Table(
        "event_losses",
        metadata,
        schema=project_name,
        autoload_with=db.bind,
    )

    # Clean loss (handles NULL and text 'NaN')
    clean_loss = func.coalesce(
        sa.cast(
            func.nullif(sa.cast(event_losses_table.c.loss, sa.String), "NaN"),
            sa.Float,
        ),
        0.0,
    )

    # Prebuild per-type totals
    loss_1_total = func.sum(
        sa.case(
            (event_losses_table.c.event_loss_type_id == 1, clean_loss),
            else_=0.0,
        )
    )
    loss_2_total = func.sum(
        sa.case(
            (event_losses_table.c.event_loss_type_id == 2, clean_loss),
            else_=0.0,
        )
    )
    loss_3_total = func.sum(
        sa.case(
            (event_losses_table.c.event_loss_type_id == 3, clean_loss),
            else_=0.0,
        )
    )

    # Compute days = floor(max_time, day) - floor(min_time, day) + 1
    # (inclusive count; if min==max same calendar day -> 1 day)
    start_day = func.date_trunc("day", func.min(event_losses_table.c.time))
    end_day = func.date_trunc("day", func.max(event_losses_table.c.time))

    # Convert interval to days via extract(epoch)/86400.0, then +1.0
    days_event = (
        func.extract("epoch", end_day - start_day) / sa.literal(86400.0)
    ) + sa.literal(1.0)

    # Avoid divide-by-zero (shouldn’t happen with min/max present, but defensive)
    days_nonzero = func.nullif(days_event, 0.0)

    stmt = (
        sa.select(
            event_losses_table.c.event_id,
            func.min(event_losses_table.c.time).label("time_min"),
            func.max(event_losses_table.c.time).label("time_max"),
            loss_1_total.label("loss_1"),
            loss_2_total.label("loss_2"),
            loss_3_total.label("loss_3"),
            # Daily = total / days (inclusive)
            (loss_1_total / days_nonzero).label("loss_1_daily"),
            (loss_2_total / days_nonzero).label("loss_2_daily"),
        )
        .where(event_losses_table.c.event_id.in_(event_ids))
        .group_by(event_losses_table.c.event_id)
    )

    result = db.execute(stmt)
    return result.fetchall()


def get_total_daily_type2_loss_open_events(
    db: Session,
    *,
    project_name: str,
) -> float:
    """
    Return the total daily loss (type 2 only) across all OPEN events (time_end IS NULL).

    Now uses the loss_daily_financial column directly from the events table.
    """
    return float(
        db.query(func.sum(models.Event.loss_daily_financial))
        .filter(models.Event.time_end.is_(None))
        .scalar()
        or 0.0
    )
