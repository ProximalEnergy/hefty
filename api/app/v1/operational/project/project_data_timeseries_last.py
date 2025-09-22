from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import core
from app.dependencies import get_project_db

router = APIRouter(
    prefix="/projects/{project_id}/data-timeseries-last",
    tags=["project_data_timeseries_last"],
)


@router.get("/")
def get_data_timeseries_last(
    project_db: Annotated[Session, Depends(get_project_db)],
    tag_ids: Annotated[list[int] | None, Query()] = None,
    device_type_ids: Annotated[list[int] | None, Query()] = None,
    sensor_type_ids: Annotated[list[int] | None, Query()] = None,
    device_ids: Annotated[list[int] | None, Query()] = None,
    include_ghost_tags: Annotated[bool, Query()] = False,
):
    data = core.crud.project.data_timeseries_last.get_data_timeseries_last(
        project_db=project_db,
        tag_ids=tag_ids,
        device_type_ids=device_type_ids,
        sensor_type_ids=sensor_type_ids,
        device_ids=device_ids,
        include_ghost_tags=include_ghost_tags,
    )

    return data.models()
