import datetime
import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import dependencies, interfaces
from app._crud.operational.calendar import (
    create_calendar_item,
    create_or_update_calendar_item_exception,
    get_calendar_item_categories,
)
from app._crud.operational.calendar import (
    delete_calendar_item as crud_delete_calendar_item,
)
from app._crud.operational.calendar import (
    update_calendar_item as crud_update_calendar_item,
)
from app._dependencies.authentication import get_user
from app.interfaces import (
    CalendarItem,
    CalendarItemCategory,
    CalendarItemCreate,
)
from core import models

router = APIRouter()


@router.get(
    "/calendar-item-categories",
    response_model=list[CalendarItemCategory],
)
async def read_calendar_item_categories(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_async_db),
    skip: int = 0,
    limit: int = 100,
):
    """Retrieve all calendar item categories.
        Even though project_id is in the path, categories are currently global.

    Args:
        project_id: Description for project_id.
        db: Description for db.
        skip: Description for skip.
        limit: Description for limit.
    """
    _ = project_id
    categories = await get_calendar_item_categories(db=db, skip=skip, limit=limit)
    return categories


@router.post("/calendar-events", response_model=CalendarItem)
async def create_calendar_item_endpoint(
    project_id: uuid.UUID,
    item: CalendarItemCreate,
    db: AsyncSession = Depends(dependencies.get_async_db),
    user_data: interfaces.UserAuthed = Depends(get_user),
):
    """Create a new calendar item for a project.

    Args:
        project_id: Description for project_id.
        item: Description for item.
        db: Description for db.
        user_data: Description for user_data.
    """
    db_item = await create_calendar_item(
        db=db, item=item, project_id=project_id, company_id=user_data.company_id
    )
    return CalendarItem.from_orm(db_item)


@router.get("/calendar-events", response_model=list[CalendarItem])
async def get_calendar_items_route(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_async_db),
    user_data: interfaces.UserAuthed = Depends(get_user),
):
    """Retrieve all calendar items for the specified project, including category color.

    Args:
        project_id: Description for project_id.
        db: Description for db.
        user_data: Description for user_data.
    """
    # Query items and eagerly load the related category and exceptions
    query = (
        select(models.CalendarItem)
        .options(
            selectinload(models.CalendarItem.category),
            selectinload(models.CalendarItem.exceptions),  # Eager load exceptions
        )
        .where(
            models.CalendarItem.project_id == project_id,
            models.CalendarItem.company_id == user_data.company_id,  # Add this filter
        )
    )
    result = await db.execute(query)
    db_items = list(result.scalars().unique().all())

    # Manually construct Pydantic models, adding the color and exdates
    result_items = []
    for item in db_items:
        item_data = CalendarItem.model_validate(
            item
        ).model_dump()  # Use model_validate for Pydantic v2
        item_data["color"] = item.category.color_code if item.category else None

        # Populate exdates for recurring events
        if item.rrule and item.exceptions:
            item_data["exdates"] = [
                exc.exception_date for exc in item.exceptions if exc.is_cancelled
            ]
        else:
            item_data["exdates"] = []  # Ensure exdates is always present, even if empty

        # Populate assignee ids and query assignments to avoid relationship issues
        assignment_model = getattr(models, "CalendarItemAssignment", None)
        if assignment_model is not None:
            assignment_query = select(assignment_model).where(
                assignment_model.calendar_item_id == item.calendar_item_id
            )
            assignment_result = await db.execute(assignment_query)
            assignments = list(assignment_result.scalars().all())
            item_data["assignee_user_ids"] = [
                a.user_id for a in assignments if a.user_id is not None
            ]
            item_data["assignee_team_ids"] = [
                a.team_id for a in assignments if a.team_id is not None
            ]
        else:
            # Fallback if CalendarItemAssignment ORM model
            # is not available in installed core
            assignment_schema = getattr(models.CalendarItem.__table__, "schema", None)
            assignment_table = sa.Table(
                "calendar_item_assignments",
                models.CalendarItem.metadata,
                schema=assignment_schema,
            )
            assignment_result = await db.execute(
                sa.select(assignment_table.c.user_id, assignment_table.c.team_id).where(
                    assignment_table.c.calendar_item_id == item.calendar_item_id
                )
            )
            rows = assignment_result.mappings().all()
            item_data["assignee_user_ids"] = [
                r["user_id"] for r in rows if r.get("user_id") is not None
            ]
            item_data["assignee_team_ids"] = [
                r["team_id"] for r in rows if r.get("team_id") is not None
            ]

        result_items.append(CalendarItem(**item_data))

    return result_items


@router.put(
    "/calendar-events/{calendar_item_id}",
    response_model=CalendarItem,
)
async def update_calendar_item_endpoint(
    project_id: uuid.UUID,
    calendar_item_id: uuid.UUID,
    item: CalendarItemCreate,
    db: AsyncSession = Depends(dependencies.get_async_db),
    user_data: interfaces.UserAuthed = Depends(get_user),
):
    """Update a calendar item.

    Args:
        project_id: The unique identifier of the project.
        calendar_item_id: Description for calendar_item_id.
        item: Description for item.
        db: Description for db.
        user_data: Description for user_data.
    """
    _ = project_id
    # Verify the item exists and belongs to the user's company
    existing_query = select(models.CalendarItem).where(
        models.CalendarItem.calendar_item_id == calendar_item_id,
        models.CalendarItem.company_id == user_data.company_id,
    )
    result = await db.execute(existing_query)
    existing_item = result.scalar_one_or_none()

    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar item with id {calendar_item_id} not found",
        )

    updated_item = await crud_update_calendar_item(
        db=db, calendar_item_id=calendar_item_id, item_in=item
    )
    return updated_item


@router.delete(
    "/calendar-events/{calendar_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_calendar_item_endpoint(
    project_id: uuid.UUID,
    calendar_item_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """Delete a calendar item by its ID.

    Args:
        project_id: The unique identifier of the project.
        calendar_item_id: Description for calendar_item_id.
        db: Description for db.
    """
    _ = project_id
    # Optional: Add ownership/permission check here using project_id and
    # user_data if necessary before allowing deletion. For now, we assume
    # if they have access to delete, it's fine.

    deleted_item = await crud_delete_calendar_item(
        db=db, calendar_item_id=calendar_item_id
    )

    if not deleted_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Calendar item with id {calendar_item_id} not found",
        )
    # No content is returned for a successful DELETE, so no explicit return value here
    return


@router.post(
    "/calendar-events/{calendar_item_id}/exceptions/{exception_date_str}",
    response_model=interfaces.CalendarItemException,
    status_code=status.HTTP_200_OK,
)
async def post_calendar_item_exception(
    project_id: uuid.UUID,
    calendar_item_id: uuid.UUID,
    exception_date_str: str,
    exception_payload: interfaces.CalendarItemExceptionUpdate,
    db: AsyncSession = Depends(dependencies.get_async_db),
):
    """Create or update an exception for a specific occurrence of a recurring
    calendar item.
        To "delete" an occurrence, pass `is_cancelled: true` in the payload.
        The `exception_date_str` in the path should be in 'YYYY-MM-DD' format.

    Args:
        project_id: Description for project_id.
        calendar_item_id: Description for calendar_item_id.
        exception_date_str: Description for exception_date_str.
        exception_payload: Description for exception_payload.
        db: Description for db.
    """
    try:
        exception_date_obj = datetime.date.fromisoformat(exception_date_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format for exception_date. Use YYYY-MM-DD.",
        )

    # Verify that the main calendar_item_id exists and belongs to the project_id
    calendar_query = select(models.CalendarItem).where(
        models.CalendarItem.calendar_item_id == calendar_item_id,
        models.CalendarItem.project_id == project_id,
    )
    calendar_result = await db.execute(calendar_query)
    db_calendar_item = calendar_result.scalar_one_or_none()

    if not db_calendar_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Calendar item with id {calendar_item_id} "
                f"not found in project {project_id}"
            ),
        )

    if not db_calendar_item.rrule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Calendar item with id {calendar_item_id} is not a "
                "recurring series. Exceptions cannot be applied."
            ),
        )

    db_exception = await create_or_update_calendar_item_exception(
        db=db,
        calendar_item_id=calendar_item_id,
        exception_date=exception_date_obj,
        exception_data=exception_payload,
    )

    # The CRUD function now returns the ORM model instance
    return db_exception  # FastAPI will convert it using the response_model
