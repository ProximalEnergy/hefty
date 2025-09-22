import datetime
from typing import Annotated
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse
from natsort import natsorted
from sqlalchemy.orm import Session

import app.utils as utils
import core
from app import dependencies, interfaces, utils
from app._crud.operational.sensor_types import get_sensor_types
from app._crud.projects.data import get_project_data as crud_get_project_data
from app.dependencies import get_db, get_project, get_project_db
from app.utils import data_df
from core import models

router = APIRouter(prefix="/projects/{project_id}", tags=["project_data"])


@router.get("/data", response_model=list[interfaces.Data])
def get_project_data(
    tag_ids: Annotated[list[int], Query()],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project_db: Session = Depends(get_project_db),
):
    if start is None or end is None:
        end = datetime.datetime.utcnow()
        start = end - datetime.timedelta(days=1)

    data = crud_get_project_data(
        project_db,
        tag_ids=tag_ids,
        start=start,
        end=end,
    )

    if len(data) == 0:
        raise HTTPException(
            status_code=404,
            detail="No data found",
        )

    df = pd.DataFrame.from_records([d.__dict__ for d in data])
    df["value"] = df.filter(regex="value_").stack().reset_index(level=1, drop=True)
    df = df[["time", "tag_id", "value"]]
    df = df.sort_values(by=["time", "tag_id"])

    records = df.to_dict("records")
    return records


def get_project_dataframe(
    *,
    tag_ids: list[int],
    sensor_type_name_shorts: list[str],
    start: datetime.datetime | None,
    end: datetime.datetime | None,
    db: Session,
    project_db: Session,
    project: models.Project,
    device_ids: list[int] = [],
    fillna_zero: bool = True,
    get_last: bool = False,
    start_offset: str = "5min",
    last_offset: str = "1h",
    ffill_limit: int | None = None,
    interval: str | None = None,
    include_ghost_tags: bool = False,
):
    # Either tag_ids or sensor_type_name_shorts must be provided
    if tag_ids == [] and sensor_type_name_shorts == [] and device_ids == []:
        raise HTTPException(
            status_code=400,
            detail="No tag_ids, sensor_type_name_shorts, or device_ids provided",
        )

    tags = core.crud.project.tags.get_project_tags(
        db=project_db,
        tag_ids=tag_ids,
        sensor_type_name_shorts=sensor_type_name_shorts,
        device_ids=device_ids,
        deep=False,
        include_ghost_tags=include_ghost_tags,
    ).models()

    if not tags:
        raise HTTPException(
            status_code=404,
            detail="No tags found for given tag_ids and sensor_type_name_shorts",
        )

    # Use default interval if none provided
    effective_interval = interval if interval is not None else "5min"

    df = data_df(
        project_db,
        project,
        tags=tags,
        start=start,
        end=end,
        fillna_zero=fillna_zero,
        get_last=get_last,
        start_offset=start_offset,
        last_offset=last_offset,
        ffill_limit=ffill_limit,
        interval=effective_interval,
    )

    sensor_types = get_sensor_types(
        db,
        sensor_type_ids=[
            tag.sensor_type_id for tag in tags if tag.sensor_type_id is not None
        ],
    )

    sensor_type_id_to_name_short = {
        sensor_type.sensor_type_id: sensor_type.name_short
        for sensor_type in sensor_types
    }

    tag_id_to_sensor_type_name_short = {
        tag.tag_id: sensor_type_id_to_name_short.get(tag.sensor_type_id) for tag in tags
    }

    # Create MultiIndex for columns
    arrays = [
        df.columns,
        [tag_id_to_sensor_type_name_short[tag_id] for tag_id in df.columns.astype(int)],
    ]
    tuples = list(zip(*arrays))
    index = pd.MultiIndex.from_tuples(
        tuples,
        names=["tag_id", "sensor_type_name_short"],
    )
    df.columns = index

    return df


@router.get("/llm-time-series")
def get_llm_time_series(
    project_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    interval: str = "base",
    tag_ids: Annotated[list[int] | None, Query()] = None,
    sensor_type_ids: Annotated[list[int] | None, Query()] = None,
):
    tags = core.crud.project.tags.get_project_tags(
        project_db,
        tag_ids=tag_ids or [],
        device_ids=[],
        sensor_type_ids=sensor_type_ids or [],
        sensor_type_name_shorts=[],
        data_type_ids=[],
        name_short="",
        name_long="",
        name_scada="",
        deep=False,
    ).models()

    if not tags:
        raise HTTPException(
            status_code=404,
            detail="No tags configured for this request",
        )

    df = utils.data_df(
        project_db,
        project,
        tags,
        start=start,
        end=end,
        agg=interval,
    )

    tag_id_to_tag_name = utils.get_tag_id_to_tag_name(project_db, tags=tags)
    tag_id_to_sensor_type_name = utils.get_tag_id_to_sensor_type_name(
        project_db,
        tags=tags,
    )
    tag_id_to_tag_name_scada = {tag.tag_id: tag.name_scada for tag in tags}

    multi_index_tuples = [
        (
            column,
            tag_id_to_tag_name[int(column)],
            tag_id_to_sensor_type_name[int(column)],
            tag_id_to_tag_name_scada[column],
        )
        for column in df.columns.astype(int)
    ]
    multi_index = pd.MultiIndex.from_tuples(
        multi_index_tuples,
        names=[
            "tag_id",
            "tag_name",
            "sensor_type_name",
            "tag_name_scada",
        ],
    )

    df.columns = multi_index
    df.index = df.index.tz_convert(project.time_zone)  # type: ignore

    return df.to_dict("tight")


@router.get("/dataframe", response_class=ORJSONResponse)
def get_project_dataframe_endpoint(
    tag_ids: Annotated[list[int], Query()] = [],
    sensor_type_name_shorts: Annotated[list[str], Query()] = [],
    device_ids: Annotated[list[int], Query()] = [],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    db: Session = Depends(get_db),
    project_db: Session = Depends(get_project_db),
    project=Depends(get_project),
    fillna_zero: bool = True,
    get_last: bool = False,
    start_offset: str = "5min",
    last_offset: str = "1h",
    ffill_limit: int | None = None,
    interval: str | None = Query(default=None),
    include_ghost_tags: bool = False,
):
    df = get_project_dataframe(
        tag_ids=tag_ids,
        sensor_type_name_shorts=sensor_type_name_shorts,
        device_ids=device_ids,
        start=start,
        end=end,
        db=db,
        project_db=project_db,
        project=project,
        fillna_zero=fillna_zero,
        get_last=get_last,
        start_offset=start_offset,
        last_offset=last_offset,
        ffill_limit=ffill_limit,
        interval=interval,
        include_ghost_tags=include_ghost_tags,
    )

    return df.to_dict("tight")


@router.get("/time-series", response_class=ORJSONResponse)
def get_time_series(
    project_id: UUID,
    tag_ids: Annotated[list[int], Query()] = [],
    device_ids: Annotated[list[int], Query()] = [],
    parent_device_id: int | None = None,
    sensor_type_ids: Annotated[list[int], Query()] = [],
    sensor_type_name_shorts: Annotated[list[str], Query()] = [],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    db: Session = Depends(dependencies.get_db),
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project),
    include_ghost_tags: Annotated[bool, Query()] = False,
    interval: Annotated[str, Query()] = "5min",
):
    if parent_device_id:
        devices = core.crud.project.devices.get_project_devices(
            project_db, parent_device_ids=[parent_device_id]
        ).models()
        device_ids_from_parent = [device.device_id for device in devices]

    else:
        device_ids_from_parent = []

    device_ids = list(set(device_ids + device_ids_from_parent))

    tags = core.crud.project.tags.get_project_tags(
        project_db,
        tag_ids=tag_ids,
        device_ids=device_ids,
        sensor_type_ids=sensor_type_ids,
        sensor_type_name_shorts=sensor_type_name_shorts,
        data_type_ids=[],
        name_short="",
        name_long="",
        name_scada="",
        deep=False,
        include_ghost_tags=include_ghost_tags,
    ).models()

    if len(tags) == 0:
        raise HTTPException(
            status_code=404,
            detail="No tags configured for this request",
        )

    df = utils.data_df(
        project_db,
        project,
        tags,
        start=start,
        end=end,
        fillna_zero=False,
        interval=interval,
    )

    tag_id_to_tag_name = utils.get_tag_id_to_tag_name(project_db, tags=tags)
    tag_id_to_sensor_type_name = utils.get_tag_id_to_sensor_type_name(
        project_db,
        tags=tags,
    )
    tag_id_to_device_name_long = utils.get_tag_id_to_device_name_long(
        project_db,
        tags=tags,
    )
    tag_id_to_tag_name_scada = {tag.tag_id: tag.name_scada for tag in tags}
    tag_id_to_tag_name_long = {
        tag.tag_id: tag.name_long if tag.name_long else "" for tag in tags
    }
    tag_id_to_device_id = {tag.tag_id: tag.device_id for tag in tags}
    tag_id_to_sensor_type_id = {tag.tag_id: tag.sensor_type_id for tag in tags}

    multi_index_tuples = [
        (
            column,
            tag_id_to_tag_name[int(column)],
            tag_id_to_sensor_type_name[int(column)],
            tag_id_to_device_name_long[int(column)],
            tag_id_to_tag_name_scada[int(column)],
            tag_id_to_tag_name_long[int(column)],
            tag_id_to_device_id[int(column)],
            tag_id_to_sensor_type_id[int(column)],
        )
        for column in df.columns
    ]
    multi_index = pd.MultiIndex.from_tuples(
        multi_index_tuples,
        names=[
            "tag_id",
            "tag_name",
            "sensor_type_name",
            "device_name_long",
            "tag_name_scada",
            "tag_name_long",
            "device_id",
            "sensor_type_id",
        ],
    )

    df.columns = multi_index

    data = [
        {
            "x": df.index.tz_convert(project.time_zone).tolist(),  # type: ignore
            "y": df[col].tolist(),
            "name": col[1],
            "sensor_type_name": col[2],
            "device_name_long": col[3],
            "tag_name_scada": col[4],
            "tag_name_long": col[5],
            "device_id": col[6],
            "sensor_type_id": col[7],
        }
        for col in df.columns
    ]

    # Sort data by tag_name_long using natsorted
    data = natsorted(data, key=lambda x: x["tag_name_long"])

    return data
