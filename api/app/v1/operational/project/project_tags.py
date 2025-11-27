import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import custom_types, interfaces, utils
from app.dependencies import get_project_db, get_project_db_async

DESCRIPTION_404 = "Tag not found"

router = APIRouter(prefix="/projects/{project_id}/tags", tags=["project_tags"])


@router.get("/", response_model=list[interfaces.Tag])
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


@router.get(
    "/{tag_id}",
    response_model=interfaces.Tag,
    responses={404: {"description": DESCRIPTION_404}},
)
def get_project_device(
    tag_id: int,
    deep: custom_types.AnnotatedDeep = False,
    project_db: Session = Depends(get_project_db),
):
    tag = core.crud.project.tags.get_project_tag(
        db=project_db, tag_id=tag_id, deep=deep
    ).model()
    utils.check_404(value=tag, detail=DESCRIPTION_404)
    return tag
