"""Calendar CRUD operations for core package."""

from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core import models
from core.db_query import DbQuery


def get_calendar_items(
    *,
    project_ids: list[UUID] | None = None,
    notifications_only: bool = False,
    include_related: bool = True,
) -> DbQuery[Any, Literal[False]]:
    """Get calendar items from the database.

    Args:
        project_ids: List of project IDs. Defaults to None.
        notifications_only: If True, only return calendar items that
            have notifications configured. Defaults to False.
        include_related: If True, eager-load relationships for SQLAlchemy output.

    Returns:
        DbQuery for calendar items with related data.
    """
    if include_related:
        stmt = (
            select(models.CalendarItem)
            # Eagerly load all relationships needed.
            .options(
                selectinload(models.CalendarItem.category),
                selectinload(models.CalendarItem.exceptions),
                selectinload(models.CalendarItem.assignments),
            )
        )
    else:
        columns = [
            getattr(models.CalendarItem, column.name)
            for column in models.CalendarItem.__table__.columns
        ]
        stmt = select(
            *columns,
            models.CalendarItemCategory.color_code.label("color"),
        ).outerjoin(
            models.CalendarItemCategory,
            models.CalendarItem.calendar_item_category_id
            == models.CalendarItemCategory.category_id,
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


def get_calendar_item_assignments(
    *,
    calendar_item_ids: list[UUID] | None = None,
) -> DbQuery[models.CalendarItemAssignment, Literal[False]]:
    """Get calendar item assignments from the database.

    Args:
        calendar_item_ids: List of calendar item IDs. Defaults to None.

    Returns:
        DbQuery for calendar item assignments.
    """
    stmt = select(models.CalendarItemAssignment)
    if calendar_item_ids:
        stmt = stmt.where(
            models.CalendarItemAssignment.calendar_item_id.in_(calendar_item_ids)
        )
    return DbQuery(query=stmt)
