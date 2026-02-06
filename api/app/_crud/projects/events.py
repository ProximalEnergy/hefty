import datetime
from typing import Any, Literal

from core.db_query import DbQuery
from sqlalchemy import Date, case, cast, func, or_, select, text

from core import models


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
    """Get project events matching optional filters.

    Args:
        device_id: Filter by a single device ID.
        time_end_gte: Filter events ending at or after this time.
        time_end_lt: Filter events ending before this time.
        open: When true, include only events without an end time.
        device_ids: Filter by a list of device IDs.
        event_ids: Filter by a list of event IDs.
        open_at: Match events open at the provided timestamp.
    """
    stmt = select(models.Event)

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
    """Get distinct device IDs that have events."""
    stmt = select(models.Event.device_id).distinct()
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
    """Get paginated project events with sorting and filters.

    Args:
        page: Zero-based page index.
        page_size: Number of records per page.
        sort_column: Column name used for sorting.
        sort_direction: Sort direction ("asc" or "desc").
        open: When true, include only events without an end time.
        device_type_id: Filter by one or more device type IDs.
        device_ids: Filter by device IDs.
        start: Filter for events active on or after this time.
        end: Filter for events active on or before this time.
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
        device_id: Filter by a single device ID.
        time_end_gte: Filter events ending at or after this time.
        time_end_lt: Filter events ending before this time.
        open: When true, include only events without an end time.
        device_ids: Filter by a list of device IDs.
        event_ids: Filter by a list of event IDs.
        open_at: Match events open at the provided timestamp.
        device_type_ids: Filter by device type IDs.
        start: Filter for events active on or after this time.
        end: Filter for events active on or before this time.
    """
    stmt = (
        select(
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
        open: Limit results to open events when True.
        start: Optional start time for filtering.
        end: Optional end time for filtering.
        device_type_ids: Optional device type ids to filter by.
        device_ids: Optional device ids to filter by.
    """
    stmt = (
        select(
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

    return DbQuery(query=stmt)
