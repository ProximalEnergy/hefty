import datetime

from sqlalchemy import Date, case, cast, func, or_, select, text
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
    """todo

    Args:
        db: TODO: describe.
        device_id: TODO: describe.
        time_end_gte: TODO: describe.
        time_end_lt: TODO: describe.
        open: TODO: describe.
        device_ids: TODO: describe.
        event_ids: TODO: describe.
        open_at: TODO: describe.
    """
    stmt = select(models.Event).options(
        selectinload(models.Event.device),
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

    result = db.execute(stmt)
    return result.scalars().all()


def get_event_device_ids(
    db: Session,
) -> list[int]:  # nosemgrep: python-enforce-keyword-only-args
    """todo

    Args:
        db: TODO: describe.
    """
    stmt = select(models.Event.device_id).distinct()
    result = db.execute(stmt)
    return list(result.scalars().all())


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
    """todo

    Args:
        db: TODO: describe.
        page: TODO: describe.
        page_size: TODO: describe.
        sort_column: TODO: describe.
        sort_direction: TODO: describe.
        open: TODO: describe.
        device_type_id: TODO: describe.
        device_ids: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    stmt = select(models.Event)
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
        stmt = stmt.add_columns(daily_loss).order_by(
            text(f"daily_loss {sort_direction} NULLS LAST"),
        )
    else:
        stmt = stmt.order_by(text(f"{sort_column} {sort_direction} NULLS LAST"))

    stmt = stmt.limit(page_size).offset(page * page_size)

    result = db.execute(stmt)
    if sort_column == "loss_daily":
        return result.all()
    return result.scalars().all()


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

    Args:
        db: TODO: describe.
        device_id: TODO: describe.
        time_end_gte: TODO: describe.
        time_end_lt: TODO: describe.
        open: TODO: describe.
        device_ids: TODO: describe.
        event_ids: TODO: describe.
        open_at: TODO: describe.
        device_type_ids: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    stmt = select(models.Event).options(
        selectinload(models.Event.device).selectinload(models.Device.device_type)
    )
    stmt = stmt.options(selectinload(models.Event.failure_mode))
    stmt = stmt.options(selectinload(models.Event.root_cause))

    # Apply filters
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

    result = db.execute(stmt)
    return result.scalars().all()


def get_events_summary(
    db: Session,
    *,
    open: bool = True,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    device_type_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
):
    """Get events with filters applied, along with device and device type information.
        This is specifically designed for generating event summaries with device info.

    Args:
        db: TODO: describe.
        open: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        device_type_ids: TODO: describe.
        device_ids: TODO: describe.
    """
    stmt = select(models.Event).options(
        selectinload(models.Event.device).selectinload(models.Device.device_type),
    )

    # Apply filters
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

    result = db.execute(stmt)
    return result.scalars().all()
