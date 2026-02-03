"""Calendar CRUD operations for core package."""

from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core import models
from core.db_query import DbQuery


def get_calendar_items(
    *,
    project_ids: list[UUID] | None = None,
    notifications_only: bool = False,
) -> DbQuery[models.CalendarItem, Literal[False]]:
    """Get calendar items from the database.

    Args:
        project_ids: List of project IDs. Defaults to None.
        notifications_only: If True, only return calendar items that
            have notifications configured. Defaults to False.

    Returns:
        DbQuery for calendar items with related data.
    """
    stmt = (
        select(models.CalendarItem)
        # Eagerly load all relationships needed.
        .options(
            selectinload(models.CalendarItem.category),
            selectinload(models.CalendarItem.exceptions),
            selectinload(models.CalendarItem.assignments),
        )
    )

    if project_ids:
        stmt = stmt.where(models.CalendarItem.project_id.in_(project_ids))

    if notifications_only:
        stmt = stmt.where(models.CalendarItem.notify_offsets.isnot(None))

    return DbQuery(query=stmt)


def get_calendar_item_exceptions(
    *,
    calendar_item_ids: list[UUID] | None = None,
) -> DbQuery[models.CalendarItemException, Literal[False]]:
    """Get calendar item exceptions from the database.

    Args:
        calendar_item_ids: List of calendar item IDs. Defaults to None.

    Returns:
        DbQuery for calendar item exceptions.
    """
    stmt = select(models.CalendarItemException)
    if calendar_item_ids:
        stmt = stmt.where(
            models.CalendarItemException.calendar_item_id.in_(calendar_item_ids)
        )
    return DbQuery(query=stmt)
