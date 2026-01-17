import datetime
from collections.abc import Iterable, Mapping
from typing import Any, Literal, cast

import sqlalchemy as sa
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, joinedload

from core import models
from core.crud.project.event_losses import get_total_daily_type2_loss_open_events
from core.db_query import DbQuery


def get_windowed_events(
    *,
    start: datetime.datetime,
    end: datetime.datetime,
    deep: bool = False,
    include_underperformance: bool = True,
) -> DbQuery[models.Event, Literal[False]]:
    """Query events that start before `end` and end after `start` or are ongoing.

    Args:
        start: TODO: describe.
        end: TODO: describe.
        deep: TODO: describe.
        include_underperformance: TODO: describe.
    """
    stmt = sa.select(models.Event).where(models.Event.time_start <= end)
    stmt = stmt.where(
        or_(models.Event.time_end >= start, models.Event.time_end.is_(None)),
    )
    options = []
    if deep:
        options.append(joinedload(models.Event.device))
    if not include_underperformance:
        options.append(joinedload(models.Event.failure_mode))
        stmt = stmt.where(
            ~models.Event.failure_mode.has(
                models.FailureMode.name_long.contains("Underperforming")
            )
        )
    if options:
        stmt = stmt.options(*options)
    return DbQuery(query=stmt)


def get_maximum_event_id(*, db: Session) -> int:
    """Return the maximum event_id in the events table.

    Args:
        db: SQLAlchemy session for querying events.
    """
    return db.scalar(sa.select(func.max(models.Event.event_id))) or 0


# ---- dynamic per-project tables (tsdb.<project>.*) ----
def get_project_tables(db: Session, *, project: str) -> tuple[sa.Table, sa.Table]:
    """Load per-project events and event_losses tables.

    Args:
        db: SQLAlchemy session used to reflect tables.
        project: Project schema name in the tsdb.
    """
    md = sa.MetaData(schema=project)
    events = sa.Table("events", md, autoload_with=db.bind)
    event_losses = sa.Table("event_losses", md, autoload_with=db.bind)
    return events, event_losses


def bulk_insert_events_returning_ids(
    db: Session,
    *,
    project: str,
    new_event_rows: Iterable[Mapping],
    events_table: sa.Table | None = None,
) -> list[int]:
    """Insert events into the project schema and return new event ids.

    Args:
        db: SQLAlchemy session for the project schema.
        project: Project schema name in the tsdb.
        new_event_rows: Iterable of event row mappings to insert.
        events_table: Optional pre-reflected events table.
    """
    if events_table is None:
        events_table, _ = get_project_tables(db, project=project)

    rows = []
    for r in new_event_rows:
        r2 = dict(r)
        r2.pop("event_id", None)  # let SERIAL/IDENTITY generate it
        rows.append(r2)
    if not rows:
        return []

    # Columns to insert (everything except event_id)
    insert_cols = [c.name for c in events_table.columns if c.name != "event_id"]

    # Build VALUES with explicit types + a client_idx to preserve input order
    typed_cols = [sa.column(c, events_table.c[c].type) for c in insert_cols]
    values_rows = [
        tuple([row.get(c) for c in insert_cols] + [i]) for i, row in enumerate(rows)
    ]
    v = sa.values(*typed_cols, sa.column("client_idx", sa.Integer()), name="v").data(
        values_rows
    )
    v_alias = v.alias("v")

    # Cast each column to the target type (prevents text inference on NULL-heavy cols)
    select_cols = [
        sa.cast(getattr(v_alias.c, c), events_table.c[c].type).label(c)
        for c in insert_cols
    ]

    # INSERT ... SELECT ... FROM v ORDER BY v.client_idx
    insert_stmt = sa.insert(events_table).from_select(
        insert_cols,
        sa.select(*select_cols).select_from(v_alias).order_by(v_alias.c.client_idx),
    )

    # IMPORTANT: Do NOT reference v in RETURNING
    insert_stmt = insert_stmt.returning(events_table.c.event_id)

    res = db.execute(insert_stmt)

    # Because we ORDER BY v.client_idx in the SELECT,
    # PostgreSQL will insert in that order and RETURNING will emit IDs in that
    # same order.
    event_ids_in_order = [r[0] for r in res]

    db.commit()

    # event_ids_in_order now aligns 1:1 with your original 'rows' order /
    # DataFrame order
    return event_ids_in_order


# ---- UPDATE existing events using VALUES (…) AS u (…) + UPDATE … FROM u ----
def bulk_update_events(
    db: Session,
    *,
    project: str,
    update_rows: Iterable[Mapping],
    events_table: sa.Table | None = None,
) -> int:
    """update_rows must include 'event_id' and the updatable fields.
        Returns count of updated rows.

    Args:
        db: SQLAlchemy session for the project schema.
        project: Project schema name in the tsdb.
        update_rows: Iterable of mappings with event_id and updates.
        events_table: Optional pre-reflected events table.
    """
    if events_table is None:
        events_table, _ = get_project_tables(db, project=project)
    rows = list(update_rows)
    if not rows:
        return 0

    # Columns we will update
    fields = (
        "time_start",
        "time_end",
        "time_last_analyzed",
        "failure_mode_id",
        "version",
    )
    cols = ("event_id",) + fields

    # --- 1) Typed VALUES block (prevents text inference for all-NULL cols) ---
    typed_cols = [sa.column(c, events_table.c[c].type) for c in cols]
    v = sa.values(*typed_cols, name="u").data(
        [[r.get(c) for c in cols] for r in rows]  # type: ignore
    )
    u = v.alias("u")

    # --- 2) Explicit casts for datetime/timestamptz in SET (belt & suspenders) ---
    set_map = {
        "time_start": sa.cast(u.c.time_start, events_table.c.time_start.type),
        "time_end": sa.cast(u.c.time_end, events_table.c.time_end.type),
        "time_last_analyzed": sa.cast(
            u.c.time_last_analyzed, events_table.c.time_last_analyzed.type
        ),
        "failure_mode_id": u.c.failure_mode_id,
        "version": u.c.version,
    }

    stmt = (
        sa.update(events_table)
        .where(events_table.c.event_id == u.c.event_id)
        .values(**set_map)
        .execution_options(synchronize_session=False)
    )

    # Execute and explicitly cast so mypy knows .rowcount exists.
    res = cast(CursorResult[Any], db.execute(stmt))
    affected = (
        res.rowcount or 0
    )  # compute before commit (consume result first if needed)
    res.close()
    db.commit()
    return affected


# ---- UPSERT event_losses on (event_id, time, event_loss_type_id) ----
def upsert_event_losses(
    db: Session,
    *,
    project: str,
    loss_rows: Iterable[Mapping],
    event_losses_table: sa.Table | None = None,
) -> int:
    """loss_rows must include: event_id, time, loss, event_loss_type_id, version.
        Performs ON CONFLICT DO UPDATE (loss, version).
        Returns number of affected rows (inserted + updated).

    Args:
        db: SQLAlchemy session for the project schema.
        project: Project schema name in the tsdb.
        loss_rows: Iterable of event loss row mappings to upsert.
        event_losses_table: Optional pre-reflected event_losses table.
    """
    if event_losses_table is None:
        _, event_losses_table = get_project_tables(db, project=project)
    rows = list(loss_rows)
    if not rows:
        return 0

    ins = pg_insert(event_losses_table).values(rows)
    stmt = ins.on_conflict_do_update(
        index_elements=[
            event_losses_table.c.event_id,
            event_losses_table.c.time,
            event_losses_table.c.event_loss_type_id,
        ],
        set_={
            "loss": ins.excluded.loss,
            "version": ins.excluded.version,
        },
    )
    # Execute and explicitly cast so mypy knows .rowcount exists.
    res = cast(CursorResult[Any], db.execute(stmt))
    affected = (
        res.rowcount or 0
    )  # compute before commit (consume result first if needed)
    res.close()
    db.commit()
    return affected


def get_events_by_id(
    *,
    event_ids: list[int],
) -> DbQuery[models.Event, Literal[False]]:
    """Build a query for events matching the provided ids.

    Args:
        event_ids: List of event ids to include.
    """
    stmt = sa.select(models.Event).where(models.Event.event_id.in_(event_ids))
    return DbQuery(query=stmt)


def get_project_events(
    *,
    device_id: int | None = None,
    time_end_gte: datetime.datetime | None = None,
    time_end_lt: datetime.datetime | None = None,
    open: bool = True,
    device_ids: list[int] | None = None,
    event_ids: list[int] | None = None,
    open_at: datetime.datetime | None = None,
) -> DbQuery[models.Event, Literal[False]]:
    """Build a query for events matching filter parameters.

    Args:
        device_id: Filter by a single device id.
        time_end_gte: Filter events ending on/after this time.
        time_end_lt: Filter events ending before this time.
        open: Include only open events when True.
        device_ids: Filter by a list of device ids.
        event_ids: Filter by a list of event ids.
        open_at: Filter events open at a specific time.
    """
    stmt = sa.select(models.Event)

    if device_id is not None:
        stmt = stmt.where(models.Event.device_id == device_id)
    if device_ids is not None:
        stmt = stmt.where(models.Event.device_id.in_(device_ids))
    if time_end_gte is not None:
        stmt = stmt.where(models.Event.time_end >= time_end_gte)
    if time_end_lt is not None:
        stmt = stmt.where(models.Event.time_end < time_end_lt)
    if open_at is not None:
        stmt = stmt.where(models.Event.time_start <= open_at)
        stmt = stmt.where(
            or_(models.Event.time_end.is_(None), models.Event.time_end > open_at),
        )
    elif open:
        stmt = stmt.where(models.Event.time_end.is_(None))
    if event_ids is not None:
        stmt = stmt.where(models.Event.event_id.in_(event_ids))

    return DbQuery(query=stmt)


def get_event_device_ids() -> DbQuery[Any, Literal[False]]:
    """Return a query for distinct device ids that have events."""
    stmt = sa.select(models.Event.device_id).distinct()
    return DbQuery(query=stmt)


def get_paginated_events(
    *,
    page: int,
    page_size: int,
    sort_column: str,
    sort_direction: str,
    open: bool,
    device_type_id: list[int] | None,
    device_ids: list[int] | None,
    start: datetime.datetime | None,
    end: datetime.datetime | None,
) -> DbQuery[models.Event, Literal[False]]:
    """Build a paginated, sortable events query.

    Args:
        page: Zero-based page index.
        page_size: Number of rows per page.
        sort_column: Column name to order by.
        sort_direction: Sort direction (ASC or DESC).
        open: Whether to include only open events.
        device_type_id: Optional list of device type ids.
        device_ids: Optional list of device ids.
        start: Window start for event overlap filtering.
        end: Window end for event overlap filtering.
    """
    stmt = sa.select(models.Event)
    if open:
        stmt = stmt.where(models.Event.time_end.is_(None))
    if device_type_id:
        stmt = stmt.where(
            models.Event.device.has(models.Device.device_type_id.in_(device_type_id)),
        )
    if device_ids:
        stmt = stmt.where(
            models.Event.device.has(models.Device.device_id.in_(device_ids)),
        )
    if start and end:
        stmt = stmt.where(models.Event.time_start <= end)
        stmt = stmt.where(
            or_(models.Event.time_end >= start, models.Event.time_end.is_(None)),
        )
    if sort_column == "loss_daily":
        daily_loss = (
            models.Event.loss_total_financial
            / sa.case(
                (
                    models.Event.time_end.is_(None),
                    sa.cast(sa.func.current_date(), sa.Date)
                    - sa.cast(models.Event.time_start, sa.Date)
                    + 1,
                ),
                else_=(
                    sa.cast(models.Event.time_end, sa.Date)
                    - sa.cast(models.Event.time_start, sa.Date)
                    + 1
                ),
            )
        ).label("daily_loss")

        stmt = stmt.add_columns(daily_loss).order_by(
            sa.text(f"daily_loss {sort_direction} NULLS LAST"),
        )
    else:
        stmt = stmt.order_by(
            sa.text(f"{sort_column} {sort_direction} NULLS LAST"),
        )

    stmt = stmt.limit(page_size).offset(page * page_size)

    return DbQuery(query=stmt)


def get_events_with_device_info(
    *,
    device_id: int | None = None,
    time_end_gte: datetime.datetime | None = None,
    time_end_lt: datetime.datetime | None = None,
    open: bool = True,
    device_ids: list[int] | None = None,
    event_ids: list[int] | None = None,
    open_at: datetime.datetime | None = None,
    device_type_ids: list[int] | None = None,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
) -> DbQuery[Any, Literal[False]]:
    """Get events with joined device and device_type information.

    This function provides a more efficient way to fetch events with their related
    device and device type data in a single query using joins.

    Args:
        device_id: Filter by a single device id.
        time_end_gte: Filter events ending on/after this time.
        time_end_lt: Filter events ending before this time.
        open: Include only open events when True.
        device_ids: Filter by a list of device ids.
        event_ids: Filter by a list of event ids.
        open_at: Filter events open at a specific time.
        device_type_ids: Filter by device type ids.
        start: Window start for event overlap filtering.
        end: Window end for event overlap filtering.
    """
    stmt = (
        sa.select(
            models.Event,
            models.Device.name_long.label("device_name_long"),
            models.DeviceType.name_long.label("device_type_name_long"),
        )
        .select_from(models.Event)
        .join(models.Device, models.Event.device_id == models.Device.device_id)
        .join(
            models.DeviceType,
            models.Device.device_type_id == models.DeviceType.device_type_id,
            isouter=True,
        )
    )

    if device_id is not None:
        stmt = stmt.where(models.Event.device_id == device_id)
    if device_ids is not None:
        stmt = stmt.where(models.Event.device_id.in_(device_ids))
    if time_end_gte is not None:
        stmt = stmt.where(models.Event.time_end >= time_end_gte)
    if time_end_lt is not None:
        stmt = stmt.where(models.Event.time_end < time_end_lt)
    if open_at is not None:
        stmt = stmt.where(models.Event.time_start <= open_at)
        stmt = stmt.where(
            or_(models.Event.time_end.is_(None), models.Event.time_end > open_at),
        )
    elif open:
        stmt = stmt.where(models.Event.time_end.is_(None))
    if event_ids is not None:
        stmt = stmt.where(models.Event.event_id.in_(event_ids))
    if device_type_ids is not None:
        stmt = stmt.where(
            models.Event.device.has(models.Device.device_type_id.in_(device_type_ids)),
        )
    if start is not None:
        stmt = stmt.where(
            or_(models.Event.time_end >= start, models.Event.time_end.is_(None)),
        )
    if end is not None:
        stmt = stmt.where(models.Event.time_start <= end)

    return DbQuery(query=stmt)


def get_events_summary(
    *,
    open: bool = True,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    device_type_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
) -> DbQuery[Any, Literal[False]]:
    """Get events with filters applied, along with device and device type information.

    This is specifically designed for generating event summaries with device info.

    Args:
        open: Include only open events when True.
        start: Window start for event overlap filtering.
        end: Window end for event overlap filtering.
        device_type_ids: Filter by device type ids.
        device_ids: Filter by device ids.
    """
    stmt = (
        sa.select(
            models.Event,
            models.Device.name_long.label("device_name_long"),
            models.DeviceType.name_long.label("device_type_name_long"),
        )
        .select_from(models.Event)
        .join(models.Device, models.Event.device_id == models.Device.device_id)
        .join(
            models.DeviceType,
            models.Device.device_type_id == models.DeviceType.device_type_id,
            isouter=True,
        )
    )

    if device_ids is not None:
        stmt = stmt.where(models.Event.device_id.in_(device_ids))
    if device_type_ids is not None:
        stmt = stmt.where(
            models.Event.device.has(models.Device.device_type_id.in_(device_type_ids)),
        )
    if start is not None:
        stmt = stmt.where(
            or_(models.Event.time_end >= start, models.Event.time_end.is_(None)),
        )
    if end is not None:
        stmt = stmt.where(models.Event.time_start <= end)
    if open:
        stmt = stmt.where(models.Event.time_end.is_(None))

    return DbQuery(query=stmt)


def get_homepage_summary(
    db: Session, *, sort_by: Literal["daily", "total"] = "daily"
) -> dict[str, Any]:
    """Summarize open events and losses for the homepage.

    Args:
        db: SQLAlchemy session for querying events.
        sort_by: Sort top events by daily or total loss.
    """
    base_stmt = (
        sa.select(func.count())
        .select_from(models.Event)
        .where(models.Event.time_end.is_(None))
    )
    total_number_of_open_events = db.scalar(base_stmt) or 0
    if total_number_of_open_events == 0:
        return {
            "top_events": [],
            "total_daily_loss": 0,
            "total_number_of_open_events": 0,
        }
    query = sa.select(models.Event).where(models.Event.time_end.is_(None))
    query = query.options(
        joinedload(models.Event.device).joinedload(models.Device.device_type)
    )
    if sort_by == "daily":
        query = query.order_by(models.Event.loss_daily_financial.desc().nullslast())
    elif sort_by == "total":
        query = query.order_by(models.Event.loss_total_financial.desc().nullslast())
    else:
        raise ValueError(f"Invalid sort_by: {sort_by}")
    top_events = db.scalars(query.limit(5)).all()

    # Build enriched top_events with device_name_full and loss_daily_financial
    enriched_top_events = []
    for event in top_events:
        device = event.device
        device_type = device.device_type if device else None
        device_type_name = device_type.name_long if device_type else "Unknown"
        device_name_full = f"{device_type_name} {device.name_long or ''}"

        # Convert event to dict and add new fields
        event_dict = {
            "event_id": event.event_id,
            "device_id": event.device_id,
            "failure_mode_id": event.failure_mode_id,
            "root_cause_id": event.root_cause_id,
            "time_start": event.time_start,
            "time_end": event.time_end,
            "time_detected": event.time_detected,
            "time_last_analyzed": event.time_last_analyzed,
            "loss_total_financial": event.loss_total_financial,
            "version": event.version,
            "device_name_full": device_name_full,
            "loss_daily_financial": event.loss_daily_financial,
        }
        enriched_top_events.append(event_dict)

    total_daily_loss = get_total_daily_type2_loss_open_events(db)
    return {
        "top_events": enriched_top_events,
        "total_daily_loss": total_daily_loss,
        "total_number_of_open_events": total_number_of_open_events,
    }
