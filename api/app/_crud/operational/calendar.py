import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app.interfaces import CalendarItemCreate, CalendarItemExceptionUpdate
from app.logger import logger
from core import models


async def get_calendar_item_categories(
    *, db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[models.CalendarItemCategory]:
    """Retrieve paginated calendar item categories.

    Args:
        db: Async database session bound to the operational schema.
        skip: Number of rows to offset for pagination.
        limit: Maximum number of categories to return.
    """
    query = select(models.CalendarItemCategory).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_calendar_item(
    *, db: AsyncSession, item: CalendarItemCreate, project_id: UUID, company_id: UUID
) -> models.CalendarItem:
    """Create a calendar item and any provided assignments.

    Args:
        db: Async database session bound to the operational schema.
        item: Calendar payload containing timing, recurrence, and notification info.
        project_id: Project that owns the calendar entry.
        company_id: Company context used when persisting the calendar item.
    """
    db_item = models.CalendarItem(
        title=item.title,
        description=item.description,
        calendar_item_category_id=item.calendar_item_category_id,
        start_time=item.start_time,
        end_time=item.end_time,
        all_day=item.all_day,
        rrule=item.rrule,
        project_id=project_id,
        company_id=company_id,  # Now passed from backend context
        timezone=item.timezone,
        notify_offsets=item.notify_offsets,
        notify_method=item.notify_method,
    )
    db.add(db_item)
    await db.flush()

    # Create assignments if provided (gracefully handle older installed core versions)
    assignment_model = getattr(models, "CalendarItemAssignment", None)

    async def insert_assignment(*, values: dict) -> None:
        """Insert a calendar assignment via model or reflected table.

        Args:
            values: Column payload identifying the calendar item and assignee.
        """
        if assignment_model is not None:
            db.add(assignment_model(**values))
            return
        # Fallback: reflect table if model is not available in installed core
        assignment_schema = getattr(models.CalendarItem.__table__, "schema", None)
        assignment_table = sa.Table(
            "calendar_item_assignments",
            models.CalendarItem.metadata,
            schema=assignment_schema,
        )
        await db.execute(sa.insert(assignment_table).values(**values))

    if getattr(item, "assignee_user_ids", None):
        for user_id in item.assignee_user_ids or []:
            await insert_assignment(
                values={
                    "calendar_item_id": db_item.calendar_item_id,
                    "user_id": user_id,
                }
            )
    if getattr(item, "assignee_team_ids", None):
        for team_id in item.assignee_team_ids or []:
            await insert_assignment(
                values={
                    "calendar_item_id": db_item.calendar_item_id,
                    "team_id": team_id,
                }
            )

    await db.commit()
    await db.refresh(db_item)
    return db_item


async def update_calendar_item(
    *, db: AsyncSession, calendar_item_id: UUID, item_in: CalendarItemCreate
) -> models.CalendarItem | None:
    """Update an existing calendar item and optionally replace assignments.

    Args:
        db: Async database session bound to the operational schema.
        calendar_item_id: Identifier for the calendar item to mutate.
        item_in: Updated calendar payload including optional assignee lists.
    """
    query = select(models.CalendarItem).where(
        models.CalendarItem.calendar_item_id == calendar_item_id
    )
    result = await db.execute(query)
    db_item = result.scalar_one_or_none()

    if not db_item:
        return None

    # Update model instance with new data (excluding assignment fields)
    update_data = item_in.model_dump(exclude_unset=True)
    assignment_user_ids = update_data.pop("assignee_user_ids", None)
    assignment_team_ids = update_data.pop("assignee_team_ids", None)
    for key, value in update_data.items():
        setattr(db_item, key, value)

    db.add(db_item)
    await db.flush()

    # Replace assignments if payload provided
    assignment_model = getattr(models, "CalendarItemAssignment", None)
    if assignment_user_ids is not None or assignment_team_ids is not None:
        # Delete existing
        if assignment_model is not None:
            delete_query = select(assignment_model).where(
                assignment_model.calendar_item_id == calendar_item_id
            )
            delete_result = await db.execute(delete_query)
            existing_assignments = delete_result.scalars().all()
            for assignment in existing_assignments:
                await db.delete(assignment)
        else:
            assignment_schema = getattr(models.CalendarItem.__table__, "schema", None)
            assignment_table = sa.Table(
                "calendar_item_assignments",
                models.CalendarItem.metadata,
                schema=assignment_schema,
            )
            await db.execute(
                assignment_table.delete().where(
                    assignment_table.c.calendar_item_id == calendar_item_id
                )
            )

        # Insert new
        async def insert_assignment(*, values: dict) -> None:
            """Insert a replacement assignment for the calendar item.

            Args:
                values: Column payload linking the calendar item to a user or team.
            """
            if assignment_model is not None:
                db.add(assignment_model(**values))
            else:
                assignment_schema_local = getattr(
                    models.CalendarItem.__table__, "schema", None
                )
                assignment_table_local = sa.Table(
                    "calendar_item_assignments",
                    models.CalendarItem.metadata,
                    schema=assignment_schema_local,
                )
                await db.execute(sa.insert(assignment_table_local).values(**values))

        for user_id in assignment_user_ids or []:
            await insert_assignment(
                values={"calendar_item_id": calendar_item_id, "user_id": user_id}
            )
        for team_id in assignment_team_ids or []:
            await insert_assignment(
                values={"calendar_item_id": calendar_item_id, "team_id": team_id}
            )

    await db.commit()
    await db.refresh(db_item)
    return db_item


async def delete_calendar_item(
    *, db: AsyncSession, calendar_item_id: UUID
) -> models.CalendarItem | None:
    """Delete a calendar item if it exists.

    Args:
        db: Async database session bound to the operational schema.
        calendar_item_id: Identifier for the calendar entry to remove.
    """
    query = select(models.CalendarItem).where(
        models.CalendarItem.calendar_item_id == calendar_item_id
    )
    result = await db.execute(query)
    db_item = result.scalar_one_or_none()

    if db_item:
        await db.delete(db_item)
        await db.commit()
        return db_item
    return None


async def create_or_update_calendar_item_exception(
    *,
    db: AsyncSession,
    calendar_item_id: UUID,
    exception_date: datetime.date,
    exception_data: CalendarItemExceptionUpdate,
) -> models.CalendarItemException:
    """Creates a new calendar item exception or updates an existing one for a given
        date.
        This is effectively an "upsert" operation based on calendar_item_id
        and exception_date.

    Args:
        db: Async database session bound to the operational schema.
        calendar_item_id: Calendar item that owns the exception record.
        exception_date: Date of the occurrence being overridden or cancelled.
        exception_data: Override payload containing cancellation and timing data.
    """

    # Prepare the statement for insert or update
    # Default is_cancelled to False if not specified, especially for new entries.
    # For overrides, if None is passed, it means clear the field in DB.
    stmt_values = {
        "calendar_item_id": calendar_item_id,
        "exception_date": exception_date,
        "is_cancelled": exception_data.is_cancelled
        if exception_data.is_cancelled is not None
        else False,
        "override_start_time": exception_data.override_start_time,
        "override_end_time": exception_data.override_end_time,
    }
    stmt: Any = insert(models.CalendarItemException).values(**stmt_values)

    # Define what to do on conflict
    # (when calendar_item_id and exception_date already exist)
    # Only update fields that are actually provided in the exception_data
    update_dict: dict[str, Any] = {}
    if exception_data.is_cancelled is not None:
        update_dict["is_cancelled"] = exception_data.is_cancelled

    # For nullable datetime fields, we need to check if the key was in the
    # payload
    # to differentiate between not providing the key vs. providing the key with
    # a null value.
    if (
        exception_data.model_fields_set
        and "override_start_time" in exception_data.model_fields_set
    ):
        update_dict["override_start_time"] = exception_data.override_start_time
    if (
        exception_data.model_fields_set
        and "override_end_time" in exception_data.model_fields_set
    ):
        update_dict["override_end_time"] = exception_data.override_end_time

    # Only include updated_at if there are fields to update and they actually
    # change something
    if update_dict:  # if there are any fields to update
        # Ensure updated_at is always set on update
        update_dict["updated_at"] = datetime.datetime.now(datetime.UTC)

    if update_dict:
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "calendar_item_id",
                "exception_date",
            ],  # Unique constraint fields
            set_=update_dict,
        )
    else:
        # If no update fields are provided (e.g. sending an empty JSON object {} ),
        # and it conflicts, do nothing.
        # If it doesn't conflict, it inserts with defaults specified in stmt_values.
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["calendar_item_id", "exception_date"],
        )

    stmt = stmt.returning(models.CalendarItemException)

    result = await db.execute(stmt)
    # Fetch the result BEFORE committing
    returned_exception = result.scalar_one_or_none()

    await db.commit()  # Commit AFTER fetching

    db_exception_to_return = None

    if returned_exception is not None:
        # If .returning() gave us a result, it's likely the one we want.
        # Refresh it to get any DB-side changes post-insert/update (e.g., from triggers)
        try:
            await db.refresh(returned_exception)
            db_exception_to_return = returned_exception
        except Exception as e:
            logger.warning(
                f"Failed to refresh CalendarItemException "
                f"(id: {
                    returned_exception.exception_id if returned_exception else 'N/A'
                }) "
                f"after upsert, will attempt re-fetch. Error: {e}",
            )
            # pass # Fallback to re-fetching is the intended behavior

    if db_exception_to_return is None:
        # This handles cases where on_conflict_do_nothing occurred
        # (returned_exception is None)
        # or if the refresh somehow failed.
        # Re-fetch the existing/created record to ensure we return the correct state.
        fetch_query = select(models.CalendarItemException).where(
            models.CalendarItemException.calendar_item_id == calendar_item_id,
            models.CalendarItemException.exception_date == exception_date,
        )
        fetch_result = await db.execute(fetch_query)
        fetched_after_commit = fetch_result.scalar_one_or_none()

        if fetched_after_commit is None:
            # This should ideally not be reached if the upsert logic is sound.
            raise HTTPException(
                status_code=500,
                detail="Failed to create or retrieve calendar item exception "
                "after upsert attempt.",
            )
        db_exception_to_return = fetched_after_commit

    return db_exception_to_return


async def get_calendar_items(
    *,
    db: AsyncSession,
    project_ids: list[UUID] | None = None,
    notifications_only: bool = False,
) -> list[models.CalendarItem]:
    """Get calendar items from the database.

    Args:
        db (AsyncSession): Database session.
        project_ids (list[UUID], optional): List of project IDs. Defaults to None.
        notifications_only (bool, optional): If True, only return calendar items
           that
           have notifications configured. Defaults to False.

    Returns:
        list[models.CalendarItem]: List of calendar items with related data.
    """
    query = (
        select(models.CalendarItem)
        # Eagerly load all relationships needed by the calling endpoint.
        .options(
            selectinload(models.CalendarItem.category),
            selectinload(models.CalendarItem.exceptions),
            selectinload(models.CalendarItem.assignments),
        )
    )

    if project_ids:
        query = query.where(models.CalendarItem.project_id.in_(project_ids))

    if notifications_only:
        query = query.where(models.CalendarItem.notify_offsets.isnot(None))

    result = await db.execute(query)
    # Use .unique() to ensure each CalendarItem is returned only once
    return list(result.scalars().unique().all())


async def get_calendar_item_exceptions(
    *,
    db: AsyncSession,
    calendar_item_ids: list[UUID] = [],
) -> list[models.CalendarItemException]:
    """Get calendar item exceptions from the database.

    Args:
        db (AsyncSession): Database session.
        calendar_item_ids (list[UUID], optional): List of calendar item IDs.
            Defaults to [].

    Returns:
        list[models.CalendarItemException]: List of calendar item exceptions.
    """
    query = select(models.CalendarItemException)
    if len(calendar_item_ids) > 0:
        query = query.where(
            models.CalendarItemException.calendar_item_id.in_(calendar_item_ids)
        )
    result = await db.execute(query)
    return list(result.scalars().all())
