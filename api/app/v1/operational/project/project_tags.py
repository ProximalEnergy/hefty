import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import custom_types, interfaces
from app.dependencies import get_project_db, get_project_db_async

router = APIRouter(prefix="/projects/{project_id}/tags", tags=["project_tags"])


@router.get("", response_model=list[interfaces.Tag])
def get_project_tags(
    tag_ids: Annotated[list[int], Query()] = [],
    in_tsdb: Annotated[bool | None, Query()] = None,
    device_ids: Annotated[list[int], Query()] = [],
    sensor_type_ids: Annotated[list[int], Query()] = [],
    device_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    name_long: str = "",
    deep: custom_types.AnnotatedDeep = False,
    include_ghost_tags: Annotated[bool, Query()] = False,
    project_db: Session = Depends(get_project_db),
):
    """todo

    Args:
        tag_ids: TODO: describe.
        in_tsdb: TODO: describe.
        device_ids: TODO: describe.
        sensor_type_ids: TODO: describe.
        device_type_ids: TODO: describe.
        name_short: TODO: describe.
        name_long: TODO: describe.
        deep: TODO: describe.
        include_ghost_tags: TODO: describe.
        project_db: TODO: describe.
    """
    return core.crud.project.tags.get_project_tags(
        db=project_db,
        tag_ids=tag_ids,
        in_tsdb=in_tsdb,
        device_ids=device_ids,
        sensor_type_ids=sensor_type_ids,
        device_type_ids=device_type_ids,
        name_short=name_short,
        name_long=name_long,
        deep=deep,
        include_ghost_tags=include_ghost_tags,
    ).models()


@router.get("/regex", response_model=list[interfaces.Tag])
async def get_tags_by_regex(
    regex: Annotated[str, Query()],
    limit: Annotated[int, Query()] = 200,
    deep: custom_types.AnnotatedDeep = False,
    project_db: AsyncSession = Depends(get_project_db_async),
):
    # Validate regex pattern before passing to database
    """todo

    Args:
        regex: TODO: describe.
        limit: TODO: describe.
        deep: TODO: describe.
        project_db: TODO: describe.
    """
    try:
        re.compile(regex)
    except re.error as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid regular expression pattern: {str(e)}",
        )
    return await core.crud.project.tags.get_tags_by_regex(
        db=project_db, regex=regex, limit=limit, deep=deep
    )
