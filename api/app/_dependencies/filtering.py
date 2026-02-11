import datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from core.crud.admin.company_projects import get_company_projects
from core.db_query import OutputType
from core.enumerations import OutputType, UserTypeEnum
from fastapi import Depends, Query

from app._dependencies.authentication import get_user
from app.dependencies import get_project_api
from app.interfaces import UserAuthed
from core import models

DATE_MIN = datetime.date(2000, 1, 1)
DATETIME_MIN = datetime.datetime(2000, 1, 1)


async def filter_project_ids_to_user(
    *,
    project_ids: list[UUID] | None = Query(None),
    user: UserAuthed = Depends(get_user),
) -> list[UUID] | None:
    """Filter project IDs to those the user is allowed to access.

    Args:
        project_ids: Optional list of project UUIDs requested by caller.
        user: Authenticated user payload to filter against.
    """
    if user.user_type_id == UserTypeEnum.SUPERADMIN:
        return project_ids

    if project_ids is None:
        return list(user.operational_project_ids)

    allowed = set(user.operational_project_ids)
    return [project_id for project_id in project_ids if project_id in allowed]


async def get_company_project_data_access_start_time(
    *,
    user: Annotated[UserAuthed, Depends(get_user)],
    project: Annotated[models.Project, Depends(get_project_api)],
) -> datetime.datetime:
    query = get_company_projects(
        company_ids=[user.company_id],
        project_ids=[project.project_id],
    )

    result = await query.get_async(output_type=OutputType.SQLALCHEMY)

    datetime_min = DATETIME_MIN.replace(tzinfo=ZoneInfo(project.time_zone))

    if len(result) == 0:
        return datetime_min
    else:
        data_access_start = result[0].data_access_start
        if data_access_start is None:
            return datetime_min
        else:
            return datetime.datetime(
                data_access_start.year,
                data_access_start.month,
                data_access_start.day,
                tzinfo=ZoneInfo(project.time_zone),
            )


async def get_company_projects_data_access_start_date(
    *,
    user: Annotated[UserAuthed, Depends(get_user)],
    project_ids: Annotated[list[UUID], Depends(filter_project_ids_to_user)],
) -> datetime.date:
    if project_ids is None:
        return DATE_MIN

    query = get_company_projects(
        company_ids=[user.company_id],
        project_ids=project_ids,
    )
    result = await query.get_async(output_type=OutputType.SQLALCHEMY)

    max_date = DATE_MIN

    for record in result:
        if record.data_access_start is not None:
            max_date = max(max_date, record.data_access_start)

    return max_date


async def filter_start_datetime_to_data_access_start_time(
    *,
    project: Annotated[models.Project, Depends(get_project_api)],
    start: datetime.datetime = Query(...),
    data_access_start_time: datetime.datetime = Depends(
        get_company_project_data_access_start_time
    ),
) -> datetime.datetime:
    start_tzinfo = start.tzinfo

    # if start is naive, localize to project local time
    if start_tzinfo is None:
        start = start.replace(tzinfo=ZoneInfo(project.time_zone))

    start = max(start, data_access_start_time)

    if start_tzinfo is None:
        start = start.replace(tzinfo=None)
    else:
        start = start.astimezone(start_tzinfo)

    return start


async def filter_start_datetime_or_none_to_date_access_start_time(
    *,
    project: Annotated[models.Project, Depends(get_project_api)],
    start: datetime.datetime | None = Query(None),
    data_access_start_time: datetime.datetime = Depends(
        get_company_project_data_access_start_time
    ),
) -> datetime.datetime | None:
    if start is None:
        return None
    return await filter_start_datetime_to_data_access_start_time(
        project=project, start=start, data_access_start_time=data_access_start_time
    )


async def filter_start_date_to_projects_data_access_start_date(
    *,
    start: datetime.date = Query(...),
    data_access_start_date: datetime.date = Depends(
        get_company_projects_data_access_start_date
    ),
) -> datetime.date:
    return max(start, data_access_start_date)


async def filter_start_date_or_none_to_projects_data_access_start_date(
    *,
    start: datetime.date | None = Query(None),
    data_access_start_date: datetime.date = Depends(
        get_company_projects_data_access_start_date
    ),
) -> datetime.date | None:
    if start is None:
        return None
    return max(start, data_access_start_date)
