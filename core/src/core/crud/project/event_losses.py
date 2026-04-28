from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Any, Literal, cast

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from core import models
from core.db_query import DbQuery
from core.enumerations import EventLossType


def get_event_losses(
    *,
    time_equals: datetime.datetime | None = None,
    time_gte: datetime.datetime | None = None,
    time_lt: datetime.datetime | None = None,
    event_ids: list[int] | None = None,
    event_loss_type_ids: list[int] | None = None,
) -> DbQuery[models.EventLoss, Literal[False]]:
    """Build a query for event losses with optional filters.

    Args:
        time_equals: Filter losses at an exact timestamp.
        time_gte: Filter losses at or after this time.
        time_lt: Filter losses before this time.
        event_ids: Filter losses for specific event ids.
    """
    stmt = sa.select(models.EventLoss)
    if time_equals is not None:
        stmt = stmt.where(models.EventLoss.time == time_equals)
    if time_gte is not None:
        stmt = stmt.where(models.EventLoss.time >= time_gte)
    if time_lt is not None:
        stmt = stmt.where(models.EventLoss.time < time_lt)
    if event_ids is not None:
        stmt = stmt.where(models.EventLoss.event_id.in_(event_ids))
    if event_loss_type_ids is not None:
        stmt = stmt.where(models.EventLoss.event_loss_type_id.in_(event_loss_type_ids))
    return DbQuery(query=stmt)


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

    Returns a dictionary mapping event_id to total loss (sum of all losses for
    that event).
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

    stmt = sa.select(
        models.EventLoss.event_id,
        func.sum(models.EventLoss.loss).label("total_loss"),
    ).where(models.EventLoss.event_id.in_(event_ids))

    if time_gte is not None:
        stmt = stmt.where(models.EventLoss.time >= time_gte)
    if time_lt is not None:
        stmt = stmt.where(models.EventLoss.time < time_lt)
    if event_loss_type_id is not None:
        stmt = stmt.where(models.EventLoss.event_loss_type_id == event_loss_type_id)

    stmt = stmt.group_by(models.EventLoss.event_id)

    results = db.execute(stmt).all()

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
    """Return per-event loss summaries from the project event_losses table.

    Args:
        db: SQLAlchemy session for the project schema.
        project_name: Project schema name to query.
        event_ids: Event ids to summarize.
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


def get_total_daily_type2_loss_open_events(  # no-star-syntax
    db: Session,
) -> float:
    """Return the total daily loss (type 2 only) across all OPEN events
    (time_end IS NULL).

        Now uses the loss_daily_financial column directly from the events table.

    Args:
        db: SQLAlchemy session for querying events.
        project_name: Project schema name for context.
    """
    return float(
        db.scalar(
            sa.select(func.sum(models.Event.loss_daily_financial)).where(
                models.Event.time_end.is_(None)
            )
        )
        or 0.0
    )


def get_5min_event_losses(
    *,
    start: datetime.datetime,
    end: datetime.datetime,
    event_loss_type_ids: list[int] | None = None,
    aggregation_column: Literal[
        "device_id", "device_type_id", "failure_mode_id", "root_cause_id"
    ]
    | None = None,
    device_ids: list[int] | None = None,
):
    """
    Get 5-minute event losses for a project, aggregated by the field of choice.
    Aggregation by "None" gives the total loss for the period.

    Args:
        project: Project model.
        start: Start datetime.
        end: End datetime.
        aggregation_column: Column to aggregate by.
    """
    el = models.EventLoss
    event_table = models.Event
    join_event = False
    join_device = False
    selected_group: sa.ColumnElement[Any] | None = None

    if device_ids is not None:
        join_event = True

    match aggregation_column:
        case "device_id":
            selected_group = cast(sa.ColumnElement[Any], event_table.device_id)
            join_event = True
        case "device_type_id":
            selected_group = cast(sa.ColumnElement[Any], models.Device.device_type_id)
            join_event = True
            join_device = True
        case "failure_mode_id":
            selected_group = cast(sa.ColumnElement[Any], event_table.failure_mode_id)
            join_event = True
        case "root_cause_id":
            # Default to unknown root cause if not set
            selected_group = sa.func.coalesce(event_table.root_cause_id, 0)
            join_event = True
        case None:
            selected_group = None
        case _:
            raise ValueError(f"Invalid aggregation column: {aggregation_column}")

    stmt = sa.select(
        el.time,
        el.event_loss_type_id,
        func.sum(el.loss).label("total_loss"),
    ).where(el.time >= start, el.time < end)

    if selected_group is not None:
        stmt = stmt.add_columns(selected_group.label(aggregation_column))

    if join_event:
        stmt = stmt.join(event_table, el.event_id == event_table.event_id)
    if join_device:
        stmt = stmt.join(
            models.Device,
            event_table.device_id == models.Device.device_id,
        )

    if event_loss_type_ids is not None:
        stmt = stmt.where(el.event_loss_type_id.in_(event_loss_type_ids))

    if device_ids is not None:
        stmt = stmt.where(event_table.device_id.in_(device_ids))

    stmt = stmt.group_by(el.time, el.event_loss_type_id)
    if selected_group is not None:
        stmt = stmt.group_by(selected_group)
        stmt = stmt.order_by(selected_group, el.event_loss_type_id, el.time)
    else:
        stmt = stmt.order_by(el.event_loss_type_id, el.time)

    return DbQuery(query=stmt)
