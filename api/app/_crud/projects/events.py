import datetime

from sqlalchemy import Date, case, cast, func, or_, text
from sqlalchemy.orm import Session, selectinload

from core import models


def get_project_events(
    db: Session,
    *,
    device_id: int | None = None,
    time_end_gte: datetime.datetime | None = None,
    time_end_lt: datetime.datetime | None = None,
    open: bool = True,
    device_ids: list[int] | None = None,
    event_ids: list[int] | None = None,
    open_at: datetime.datetime | None = None,
):
    query = db.query(models.Event)

    query = query.options(
        selectinload(models.Event.device),
    )

    if device_id is not None:
        query = query.filter(models.Event.device_id == device_id)
    if device_ids is not None:
        query = query.filter(models.Event.device_id.in_(device_ids))
    if time_end_gte is not None:
        query = query.filter(models.Event.time_end >= time_end_gte)
    if time_end_lt is not None:
        query = query.filter(models.Event.time_end < time_end_lt)
    if open_at is not None:
        query = query.filter(models.Event.time_start <= open_at)
        query = query.filter(
            or_(models.Event.time_end.is_(None), models.Event.time_end > open_at),
        )
    elif open:
        query = query.filter(models.Event.time_end.is_(None))
    if event_ids is not None:
        query = query.filter(models.Event.event_id.in_(event_ids))

    return query.all()


def get_event_device_ids(db: Session) -> list[int]:  # skip-star-syntax
    query = db.query(models.Event)
    query = query.distinct(models.Event.device_id)
    query_return = query.all()
    device_ids = [x.device_id for x in query_return]
    return device_ids


def get_project_events_by_id(
    db: Session,
    *,
    event_id: int | list | None = None,
    open: bool = True,
    deep: bool = True,
):
    query = db.query(models.Event)
    if isinstance(event_id, list):
        query = query.filter(models.Event.event_id.in_(event_id))
    elif event_id is not None:
        query = query.filter(models.Event.event_id == event_id)
    if open:
        query = query.filter(models.Event.time_end.is_(None))
    if deep:
        query = query.options(selectinload(models.Event.device))
    return query.all()


def get_paginated_events(
    db: Session,
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
):
    query = db.query(models.Event)
    if open:
        query = query.filter(models.Event.time_end.is_(None))
    if device_type_id:
        query = query.filter(
            models.Event.device.has(models.Device.device_type_id.in_(device_type_id)),
        )
    if device_ids:
        query = query.filter(
            models.Event.device.has(models.Device.device_id.in_(device_ids)),
        )
    if start and end:
        query = query.filter(models.Event.time_start <= end)
        query = query.filter(
            or_(models.Event.time_end >= start, models.Event.time_end.is_(None)),
        )
    # Handle special case for sorting by daily loss
    if sort_column == "loss_daily":
        daily_loss = (
            models.Event.loss_total_financial
            / case(
                (
                    models.Event.time_end.is_(None),
                    cast(func.current_date(), Date)
                    - cast(models.Event.time_start, Date)
                    + 1,
                ),
                else_=(
                    cast(models.Event.time_end, Date)
                    - cast(models.Event.time_start, Date)
                    + 1
                ),
            )
        ).label("daily_loss")

        # removed this line for making sure daily loss doesn't show No active Events!:
        # query = query.filter(models.Event.loss_total_financial.isnot(None))
        query = query.add_columns(daily_loss).order_by(
            text(f"daily_loss {sort_direction} NULLS LAST"),
        )
    else:
        query = query.order_by(text(f"{sort_column} {sort_direction} NULLS LAST"))

    query = query.limit(page_size).offset(page * page_size)

    return query.all()


def get_events_with_device_info(
    db: Session,
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
):
    """Get events with joined device and device_type information.

    This function provides a more efficient way to fetch events with their related
    device and device type data in a single query using joinedload.
    """
    query = db.query(models.Event).options(
        selectinload(models.Event.device).selectinload(models.Device.device_type)
    )
    query = query.options(selectinload(models.Event.failure_mode))
    query = query.options(selectinload(models.Event.root_cause))

    # Apply filters
    if device_id is not None:
        query = query.filter(models.Event.device_id == device_id)
    if device_ids is not None:
        query = query.filter(models.Event.device_id.in_(device_ids))
    if time_end_gte is not None:
        query = query.filter(models.Event.time_end >= time_end_gte)
    if time_end_lt is not None:
        query = query.filter(models.Event.time_end < time_end_lt)
    if open_at is not None:
        query = query.filter(models.Event.time_start <= open_at)
        query = query.filter(
            or_(models.Event.time_end.is_(None), models.Event.time_end > open_at),
        )
    elif open:
        query = query.filter(models.Event.time_end.is_(None))
    if event_ids is not None:
        query = query.filter(models.Event.event_id.in_(event_ids))
    if device_type_ids is not None:
        query = query.filter(
            models.Event.device.has(models.Device.device_type_id.in_(device_type_ids)),
        )
    if start is not None:
        query = query.filter(
            or_(models.Event.time_end >= start, models.Event.time_end.is_(None)),
        )
    if end is not None:
        query = query.filter(models.Event.time_start <= end)

    return query.all()


def get_events_summary(
    db: Session,
    *,
    open: bool = True,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    device_type_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
):
    """
    Get events with filters applied, along with device and device type information.
    This is specifically designed for generating event summaries with device info.
    """
    query = db.query(models.Event).options(
        selectinload(models.Event.device).selectinload(models.Device.device_type),
    )

    # Apply filters
    if device_ids is not None:
        query = query.filter(models.Event.device_id.in_(device_ids))
    if device_type_ids is not None:
        query = query.filter(
            models.Event.device.has(models.Device.device_type_id.in_(device_type_ids)),
        )
    if start is not None:
        query = query.filter(
            or_(models.Event.time_end >= start, models.Event.time_end.is_(None)),
        )
    if end is not None:
        query = query.filter(models.Event.time_start <= end)
    if open:
        query = query.filter(models.Event.time_end.is_(None))

    return query.all()


def get_count_open(
    *,
    db: Session,
):
    query = db.query(models.Event)
    query = query.filter(models.Event.time_end.is_(None))
    return query.count()


def get_maximum_event_id(
    *,
    db: Session,
) -> int:
    """Get the maximum event_id from the events table.

    Returns 0 if no events exist in the table.
    """
    result = db.query(func.max(models.Event.event_id)).scalar()
    return result if result is not None else 0
