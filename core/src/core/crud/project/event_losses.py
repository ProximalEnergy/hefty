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
from core.enumerations import EventLossType
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
    """TODO: add description.

    Args:
        db: TODO: describe.
        time_equals: TODO: describe.
        time_gte: TODO: describe.
        time_lt: TODO: describe.
        event_ids: TODO: describe.
        return_query: TODO: describe.
    """
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


def get_event_losses_aggregated(
    db: Session,
    *,
    time_gte: datetime.datetime | None = None,
    time_lt: datetime.datetime | None = None,
    event_ids: list[int] | None = None,
    event_loss_type_id: int | None = None,
) -> dict[int, float]:
    """
    Get aggregated event losses by event_id.

    Returns a dictionary mapping event_id to total loss (sum of all losses for that event).
    This is much more efficient than fetching all individual loss records when you only
    need the aggregated sum per event.

    Args:
        db: Database session
        time_gte: Filter losses where time >= this value
        time_lt: Filter losses where time < this value
        event_ids: Filter by these event IDs (if None, returns empty dict)
        event_loss_type_id: Filter by this loss type ID (if None, includes all types)

    Returns:
        Dictionary mapping event_id to total loss (float)
    """
    if not event_ids:
        return {}

    query = db.query(
        models.EventLoss.event_id,
        func.sum(models.EventLoss.loss).label("total_loss"),
    )

    query = query.filter(models.EventLoss.event_id.in_(event_ids))

    if time_gte is not None:
        query = query.filter(models.EventLoss.time >= time_gte)
    if time_lt is not None:
        query = query.filter(models.EventLoss.time < time_lt)
    if event_loss_type_id is not None:
        query = query.filter(models.EventLoss.event_loss_type_id == event_loss_type_id)

    query = query.group_by(models.EventLoss.event_id)

    results = query.all()

    # Convert to dictionary: event_id -> total_loss
    # func.sum() returns None if no rows match, so we default to 0.0
    return {
        row.event_id: float(row.total_loss if row.total_loss is not None else 0.0)
        for row in results
    }


def get_event_losses_summary_in_sql(
    db: Session,
    *,
    project_name: str,
    event_ids: list[int],
) -> Sequence[Row[Any]]:
    # Early return for empty list to avoid IN ()
    """TODO: add description.

    Args:
        db: TODO: describe.
        project_name: TODO: describe.
        event_ids: TODO: describe.
    """
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
            (
                event_losses_table.c.event_loss_type_id
                == EventLossType.PROXIMAL_ENERGY,
                clean_loss,
            ),
            else_=0.0,
        )
    )
    loss_2_total = func.sum(
        sa.case(
            (
                event_losses_table.c.event_loss_type_id
                == EventLossType.PROXIMAL_FINANCIAL,
                clean_loss,
            ),
            else_=0.0,
        )
    )
    loss_3_total = func.sum(
        sa.case(
            (
                event_losses_table.c.event_loss_type_id
                == EventLossType.PROXIMAL_PV_DC_CAPACITY,
                clean_loss,
            ),
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
    """Return the total daily loss (type 2 only) across all OPEN events (time_end IS NULL).

        Now uses the loss_daily_financial column directly from the events table.

    Args:
        db: TODO: describe.
        project_name: TODO: describe.
    """
    return float(
        db.query(func.sum(models.Event.loss_daily_financial))
        .filter(models.Event.time_end.is_(None))
        .scalar()
        or 0.0
    )
