import datetime
from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

import pandas as pd
from core.crud.operational.sensor_types import get_sensor_types
from core.dependencies import get_db, get_db_async
from core.enumerations import TimeInterval
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse
from natsort import natsorted
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import app.utils as utils
import core
from app import interfaces
from app._crud.projects.data import get_project_data as crud_get_project_data
from app.dependencies import get_project_api, get_project_db
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
    """todo

    Args:
        tag_ids: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        project_db: TODO: describe.
    """
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
        return []

    df = pd.DataFrame.from_records([d.__dict__ for d in data])
    df["value"] = df.filter(regex="value_").stack().reset_index(level=1, drop=True)
    df = df[["time", "tag_id", "value"]]
    df = df.sort_values(by=["time", "tag_id"])

    records = df.to_dict("records")
    return records


def get_project_dataframe(
    *,
    tag_ids: list[int],
    sensor_type_ids: Sequence[int],
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
    """todo

    Args:
        tag_ids: TODO: describe.
        sensor_type_ids: TODO: describe.
        sensor_type_name_shorts: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
        device_ids: TODO: describe.
        fillna_zero: TODO: describe.
        get_last: TODO: describe.
        start_offset: TODO: describe.
        last_offset: TODO: describe.
        ffill_limit: TODO: describe.
        interval: TODO: describe.
        include_ghost_tags: TODO: describe.
    """
    if (
        tag_ids == []
        and sensor_type_name_shorts == []
        and sensor_type_ids == []
        and device_ids == []
    ):
        raise HTTPException(
            status_code=400,
            detail="No tag_ids, sensor_type_name_shorts, sensor_type_ids, or device_ids provided",
        )

    tags = core.crud.project.tags.get_project_tags(
        db=project_db,
        tag_ids=tag_ids,
        sensor_type_ids=sensor_type_ids,
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
    ).models()

    sensor_type_id_to_name_short = {
        sensor_type.sensor_type_id: sensor_type.name_short
        for sensor_type in sensor_types
    }

    tag_id_to_sensor_type_name_short: dict[int, str] = {}
    for tag in tags:
        sensor_type_id = tag.sensor_type_id
        if sensor_type_id is None:
            tag_id_to_sensor_type_name_short[tag.tag_id] = ""
            continue

        tag_id_to_sensor_type_name_short[tag.tag_id] = sensor_type_id_to_name_short.get(
            sensor_type_id, ""
        )

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
    project: Annotated[models.Project, Depends(get_project_api)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    interval: str = "base",
    tag_ids: Annotated[list[int] | None, Query()] = None,
    sensor_type_ids: Annotated[list[int] | None, Query()] = None,
):
    """todo

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        interval: TODO: describe.
        tag_ids: TODO: describe.
        sensor_type_ids: TODO: describe.
    """
    tags = core.crud.project.tags.get_project_tags(
        project_db,
        tag_ids=tag_ids or [],
        sensor_type_ids=sensor_type_ids or [],
        name_scada="",
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
    project=Depends(get_project_api),
    fillna_zero: bool = True,
    get_last: bool = False,
    start_offset: str = "5min",
    last_offset: str = "1h",
    ffill_limit: int | None = None,
    interval: str | None = Query(default=None),
    include_ghost_tags: bool = False,
):
    """todo

    Args:
        tag_ids: TODO: describe.
        sensor_type_name_shorts: TODO: describe.
        device_ids: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
        fillna_zero: TODO: describe.
        get_last: TODO: describe.
        start_offset: TODO: describe.
        last_offset: TODO: describe.
        ffill_limit: TODO: describe.
        interval: TODO: describe.
        include_ghost_tags: TODO: describe.
    """
    df = get_project_dataframe(
        tag_ids=tag_ids,
        sensor_type_ids=[],
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
    db: Session = Depends(get_db),
    project_db: Session = Depends(get_project_db),
    project: models.Project = Depends(get_project_api),
    include_ghost_tags: Annotated[bool, Query()] = False,
    interval: Annotated[str, Query()] = "5min",
):
    """todo

    Args:
        project_id: TODO: describe.
        tag_ids: TODO: describe.
        device_ids: TODO: describe.
        parent_device_id: TODO: describe.
        sensor_type_ids: TODO: describe.
        sensor_type_name_shorts: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
        include_ghost_tags: TODO: describe.
        interval: TODO: describe.
    """
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
        name_scada="",
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


## This is a temporary endpoint, eventually we will replace the above with DataTimeseries.get()
@router.get("/data-timeseries-v3", response_model=list[interfaces.DataTimeSeries])
async def get_timeseries_v3(
    project_db: Annotated[Session, Depends(get_project_db)],
    operational_db: Annotated[AsyncSession, Depends(get_db_async)],
    project: Annotated[models.Project, Depends(get_project_api)],
    tag_ids: Annotated[list[int], Query()] = [],
    sensor_type_ids: Annotated[list[int], Query()] = [],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    interval: str | None = None,
    ensure_full_range: bool = False,
    cutoff_now: bool = False,
):
    """todo

    Args:
        project_db: TODO: describe.
        operational_db: TODO: describe.
        project: TODO: describe.
        tag_ids: TODO: describe.
        sensor_type_ids: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        interval: TODO: describe.
        ensure_full_range: TODO: describe.
        cutoff_now: TODO: describe.
    """
    if tag_ids == [] and sensor_type_ids == []:
        return []

    # Validate required parameters
    if start is None or end is None:
        raise HTTPException(
            status_code=400, detail="start and end datetime parameters are required"
        )

    valid_intervals = [time_interval.value for time_interval in TimeInterval]

    if interval is None:
        agg_interval = TimeInterval.FIVE_MINUTES
    else:
        try:
            agg_interval = TimeInterval(interval)
        except ValueError as exc:  # pragma: no cover - runtime validation
            valid_options = ", ".join(valid_intervals)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid interval '{interval}'. Valid intervals are: {valid_options}"
                ),
            ) from exc

    data_timeseries = await core.crud.project.data_timeseries.DataTimeseries.get(
        project_db=project_db,
        operational_db=operational_db,
        project_name_short=project.name_short,
        tag_ids=tag_ids,
        sensor_type_ids=sensor_type_ids,
        query_start=start,
        query_end=end,
        return_arrow=False,
        agg_interval=agg_interval,
        ensure_full_range=ensure_full_range,
    )

    # Convert polars DataFrame to pandas
    df = data_timeseries.df.to_pandas()

    if cutoff_now:
        if "time" in df.columns:
            df = df[df["time"] <= pd.Timestamp.now(tz=project.time_zone)]
        elif "time_bucket" in df.columns:
            df = df[df["time_bucket"] <= pd.Timestamp.now(tz=project.time_zone)]
        else:
            raise ValueError("time or time_bucket column not found in dataframe")

    # Get tags for metadata
    if tag_ids:
        tags = core.crud.project.tags.get_project_tags(
            project_db,
            tag_ids=tag_ids,
            deep=True,
        ).models()
    else:
        tags = core.crud.project.tags.get_project_tags(
            project_db,
            sensor_type_ids=sensor_type_ids,
            deep=True,
        ).models()

    # Build metadata mappings
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

    # Get time column name (could be 'time' or 'time_bucket')
    # Check if time is in index or columns
    # time_series can be either DatetimeIndex or Series[Timestamp]
    time_series: pd.DatetimeIndex | pd.Series[pd.Timestamp]
    if df.index.name in ["time", "time_bucket"]:
        time_col = df.index.name
        time_series = pd.to_datetime(df.index)
        # Apply ffill() then fillna(0) to all columns (time is in index)
        data_columns: list[str] = list(df.columns)
        df[data_columns] = df[data_columns].ffill().fillna(0)
    elif "time" in df.columns:
        time_col = "time"
        time_series = pd.to_datetime(df[time_col])
        # Apply ffill() then fillna(0) to all columns except time
        data_columns = [col for col in df.columns if col != time_col]
        df[data_columns] = df[data_columns].ffill().fillna(0)
    elif "time_bucket" in df.columns:
        time_col = "time_bucket"
        time_series = pd.to_datetime(df[time_col])
        # Apply ffill() then fillna(0) to all columns except time_bucket
        data_columns = [col for col in df.columns if col != time_col]
        df[data_columns] = df[data_columns].ffill().fillna(0)
    else:
        return []

    # Convert to project timezone
    # Handle both DatetimeIndex and Series
    if isinstance(time_series, pd.DatetimeIndex):
        # DatetimeIndex has timezone methods directly, not through .dt
        if time_series.tz is None:
            time_series = time_series.tz_localize(project.time_zone)
        else:
            time_series = time_series.tz_convert(project.time_zone)
    else:
        # Series uses .dt accessor
        if time_series.dt.tz is None:
            time_series = time_series.dt.tz_localize(project.time_zone)
        else:
            time_series = time_series.dt.tz_convert(project.time_zone)

    # Convert to ISO format strings
    if isinstance(time_series, pd.DatetimeIndex):
        time_strings = time_series.strftime("%Y-%m-%dT%H:%M:%S%z").tolist()
    else:
        time_strings = time_series.dt.strftime("%Y-%m-%dT%H:%M:%S%z").tolist()

    # Transform each tag column into a DataTimeSeries object
    data = []
    # Get columns to iterate over (exclude time column if it's a column, not index)
    columns_to_process = [col for col in df.columns if col != time_col]

    for col in columns_to_process:
        # Column should be tag_id (integer)
        try:
            tag_id = int(col)
        except (ValueError, TypeError):
            continue

        # Get tag metadata
        tag_name = tag_id_to_tag_name.get(tag_id, "")
        sensor_type_name = tag_id_to_sensor_type_name.get(tag_id, "")
        device_name_long = tag_id_to_device_name_long.get(tag_id, "")
        tag_name_scada = tag_id_to_tag_name_scada.get(tag_id, "")
        tag_name_long = tag_id_to_tag_name_long.get(tag_id, "")
        device_id = tag_id_to_device_id.get(tag_id)
        sensor_type_id = tag_id_to_sensor_type_id.get(tag_id)

        # Get values and convert to list, handling None/NaN
        values = df[col].tolist()
        y_values = [
            float(val) if val is not None and pd.notna(val) else None for val in values
        ]

        # Include tag_id in the trace data for matching in frontend
        trace_data = {
            "x": time_strings,
            "y": y_values,
            "y_range": y_values,  # y_range same as y for now
            "yaxis": "y",
            "name": tag_name_scada,  # Use tag_name_scada as the trace name
            "sensor_type_name": sensor_type_name,
            "device_name_long": device_name_long,
            "tag_name_scada": tag_name_scada,
            "tag_name_long": tag_name_long,
            "device_id": device_id if device_id is not None else 0,
            "sensor_type_id": sensor_type_id if sensor_type_id is not None else 0,
            "tag_id": tag_id,  # Include tag_id for matching
        }
        data.append(trace_data)

    # Sort data by tag_name_long using natsorted
    # Cast to str to ensure type safety for natsorted key function
    data = natsorted(data, key=lambda x: str(x["tag_name_long"] or ""))

    return data
