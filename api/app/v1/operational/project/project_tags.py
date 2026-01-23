import re
from typing import Annotated

import pandas as pd
from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

import core
from app import custom_types, interfaces
from app.dependencies import (
    get_project_db_async,
    get_project_name_short_async,
)

router = APIRouter(prefix="/projects/{project_id}/tags", tags=["project_tags"])


@router.get("/", response_model=list[interfaces.Tag])
async def get_project_tags(
    tag_ids: Annotated[list[int], Query()] = [],
    in_tsdb: Annotated[bool | None, Query()] = None,
    device_ids: Annotated[list[int], Query()] = [],
    sensor_type_ids: Annotated[list[int], Query()] = [],
    device_type_ids: Annotated[list[int], Query()] = [],
    sensor_type_name_shorts: Annotated[list[str], Query()] = [],
    data_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    name_long: str = "",
    name_scada: str = "",
    deep: custom_types.AnnotatedDeep = False,
    include_ghost_tags: Annotated[bool, Query()] = False,
    has_sensor_type_id: Annotated[bool, Query()] = False,
    project_schema: Annotated[str, Depends(get_project_name_short_async)] = "",
):
    """todo

    Args:
        tag_ids: TODO: describe.
        in_tsdb: TODO: describe.
        device_ids: TODO: describe.
        sensor_type_ids: TODO: describe.
        device_type_ids: TODO: describe.
        sensor_type_name_shorts: TODO: describe.
        data_type_ids: TODO: describe.
        name_short: TODO: describe.
        name_long: TODO: describe.
        name_scada: TODO: describe.
        deep: TODO: describe.
        include_ghost_tags: TODO: describe.
        has_sensor_type_id: TODO: describe.
        project_schema: TODO: describe.
    """
    tags_query = core.crud.project.tags.get_project_tags_v2(
        tag_ids=tag_ids,
        in_tsdb=in_tsdb,
        device_ids=device_ids,
        sensor_type_ids=sensor_type_ids,
        device_type_ids=device_type_ids,
        sensor_type_name_shorts=sensor_type_name_shorts,
        data_type_ids=data_type_ids,
        name_short=name_short,
        name_long=name_long,
        name_scada=name_scada,
        deep=deep,
        include_ghost_tags=include_ghost_tags,
        has_sensor_type_id=has_sensor_type_id,
    )
    df = await tags_query.get_async(
        output_type=OutputType.PANDAS, schema=project_schema
    )

    # Convert geography columns to serializable dicts
    for col in df.columns:
        if "point" in col or "polygon" in col:
            df[col] = df[col].apply(lambda x: interfaces.convert(WKBElement=x))

    # Convert to dict and replace NaN/NA with None for Pydantic validation
    # This avoided pandas FutureWarnings regarding downcasting and is very reliable
    return [
        {k: (None if pd.isna(v) else v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]


@router.get("/regex", response_model=list[interfaces.TagV1])
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
