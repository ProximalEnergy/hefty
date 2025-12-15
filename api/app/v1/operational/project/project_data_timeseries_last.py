from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import core
from app.dependencies import get_project_db

router = APIRouter(
    prefix="/projects/{project_id}/data-timeseries-last",
    tags=["project_data_timeseries_last"],
)


@router.get("")
def get_data_timeseries_last(
    project_db: Annotated[Session, Depends(get_project_db)],
    tag_ids: Annotated[list[int] | None, Query()] = None,
    device_type_ids: Annotated[list[int] | None, Query()] = None,
    sensor_type_ids: Annotated[list[int] | None, Query()] = None,
    device_ids: Annotated[list[int] | None, Query()] = None,
    include_ghost_tags: Annotated[bool, Query()] = False,
):
    """todo

    Args:
        project_db: TODO: describe.
        tag_ids: TODO: describe.
        device_type_ids: TODO: describe.
        sensor_type_ids: TODO: describe.
        device_ids: TODO: describe.
        include_ghost_tags: TODO: describe.
    """
    data = core.crud.project.data_timeseries_last.get_data_timeseries_last(
        project_db=project_db,
        tag_ids=tag_ids,
        device_type_ids=device_type_ids,
        sensor_type_ids=sensor_type_ids,
        device_ids=device_ids,
        include_ghost_tags=include_ghost_tags,
        deep=True,
    )

    # Only call .models() once so we don’t re-hit the DB
    models_ = data.models()

    for d in models_:
        tag = d.tag
        if tag is None:
            continue

        # Pull scale/offset once, with cheap defaults
        scale = tag.unit_scale if tag.unit_scale is not None else 1
        offset = tag.unit_offset if tag.unit_offset is not None else 0

        # Skip work if no transform
        if scale != 1 or offset != 0:
            # Use `is not None` so zero values are correctly transformed
            if d.value_bigint is not None:
                d.value_bigint = d.value_bigint * scale + offset
            if d.value_double is not None:
                d.value_double = d.value_double * scale + offset
            if d.value_real is not None:
                d.value_real = d.value_real * scale + offset
            if d.value_integer is not None:
                d.value_integer = d.value_integer * scale + offset

        # Drop relationship so it doesn’t go into the JSON
        d.tag = None

    return models_
