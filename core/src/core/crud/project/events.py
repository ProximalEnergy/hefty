import datetime
from collections.abc import Iterable, Mapping
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, noload, selectinload

from core import models
from core.model_list import ModelList


def get_windowed_events(
    db: Session,
    *,
    start: datetime.datetime,
    end: datetime.datetime,
    deep: bool = False,
    return_query: bool = False,
) -> ModelList[models.Event]:
    """Query events that start before `end` and end after `start` or are ongoing."""
    query = db.query(models.Event)
    query = query.filter(models.Event.time_start <= end)
    query = query.filter(
        or_(models.Event.time_end >= start, models.Event.time_end.is_(None)),
    )
    if deep:
        query = query.options(selectinload(models.Event.device))
    else:
        query = query.options(noload(models.Event.device))
    return ModelList(query=query, return_query=return_query)


def get_maximum_event_id(db: Session) -> int:  # skip-star-syntax
    return db.query(func.max(models.Event.event_id)).scalar() or 0


# ---- dynamic per-project tables (tsdb.<project>.*) ----
def get_project_tables(db: Session, *, project: str) -> tuple[sa.Table, sa.Table]:
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
    v = sa.values(*typed_cols, sa.column("client_idx", sa.Integer()), name="v").data(
        [[row.get(c) for c in insert_cols] + [i] for i, row in enumerate(rows)]  # type: ignore
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
    # PostgreSQL will insert in that order and RETURNING will emit IDs in that same order.
    event_ids_in_order = [r[0] for r in res]

    db.commit()

    # event_ids_in_order now aligns 1:1 with your original 'rows' order / DataFrame order
    return event_ids_in_order


# ---- UPDATE existing events using VALUES (…) AS u (…) + UPDATE … FROM u ----
def bulk_update_events(
    db: Session,
    *,
    project: str,
    update_rows: Iterable[Mapping],
    events_table: sa.Table | None = None,
) -> int:
    """
    update_rows must include 'event_id' and the updatable fields.
    Returns count of updated rows.
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
    v = sa.values(*typed_cols, name="u").data([[r.get(c) for c in cols] for r in rows])  # type: ignore
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
    """
    loss_rows must include: event_id, time, loss, event_loss_type_id, version.
    Performs ON CONFLICT DO UPDATE (loss, version).
    Returns number of affected rows (inserted + updated).
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


def get_events_by_id(db: Session, *, event_ids: list[int]) -> ModelList[models.Event]:
    return ModelList(
        query=db.query(models.Event).filter(models.Event.event_id.in_(event_ids)),
        return_query=False,
    )
