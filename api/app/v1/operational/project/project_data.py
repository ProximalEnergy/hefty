import datetime
from types import SimpleNamespace
from typing import Annotated, cast

import pandas as pd
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import TimeInterval
from fastapi import APIRouter, Depends, HTTPException, Query
from natsort import natsorted
from sqlalchemy.orm import Session

import app.utils as utils
import core
from app import interfaces
from app._dependencies.filtering import (
    filter_start_datetime_or_none_to_date_access_start_time,
)
from app.dependencies import get_project_api, get_project_db
from core import models

router = APIRouter(
    prefix="",
    tags=["project_data"],
)


@router.get("/llm-time-series")
async def get_llm_time_series(
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
    start: Annotated[
        datetime.datetime | None,
        Depends(filter_start_datetime_or_none_to_date_access_start_time),
    ] = None,
    end: datetime.datetime | None = None,
    interval: str = "5min",
    tag_ids: Annotated[list[int] | None, Query()] = None,
    sensor_type_ids: Annotated[list[int] | None, Query()] = None,
):
    """todo

    Args:
        project_db: Description for project_db.
        project: Description for project.
        start: Description for start.
        end: Description for end.
        interval: Pandas offset alias when defaulting ``end`` via ``ceil``.
        tag_ids: Description for tag_ids.
        sensor_type_ids: Description for sensor_type_ids.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    tags_df = await core.crud.project.tags.get_project_tags_v2(
        tag_ids=tag_ids or [],
        sensor_type_ids=sensor_type_ids or [],
        name_scada="",
    ).get_async(output_type=OutputType.POLARS, schema=project_schema)

    if tags_df is None or tags_df.is_empty():
        raise HTTPException(
            status_code=404,
            detail="No tags configured for this request",
        )
    tags = [SimpleNamespace(**row) for row in tags_df.to_dicts()]

    # If start is None, set to beginning of day
    if start is None:
        start = pd.Timestamp.now(tz=project.time_zone).floor("D")
    else:
        start = pd.Timestamp(start)
        # If start is naive, localize to project time zone
        if start.tzinfo is None:
            start = start.tz_localize(project.time_zone)
        # If start is in different time zone, convert to project time zone
        else:
            start = start.tz_convert(project.time_zone)

    # If end is None, set to end of day
    if end is None:
        end = pd.Timestamp.now(tz=project.time_zone).ceil(interval)
    else:
        end = pd.Timestamp(end)
        # If end is naive, localize to project time zone
        if end.tzinfo is None:
            end = end.tz_localize(project.time_zone)
        # If end is in different time zone, convert to project
        else:
            end = end.tz_convert(project.time_zone)

    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=tags_df,
        query_start=start,
        query_end=end,
        project_db=project_db,
        freq=TimeInterval.FIVE_MINUTES,
    ).get()

    df = data_timeseries_instance.df.to_pandas()
    df = df.set_index("time")
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
    df.columns = df.columns.astype(int)

    tag_id_to_tag_name = await utils.get_tag_id_to_tag_name(
        tags=tags,
    )
    tag_id_to_sensor_type_name = await utils.get_tag_id_to_sensor_type_name(
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
    df.index = df.index.tz_convert(project.time_zone)

    return df.to_dict("tight")


@router.get("/time-series")
async def get_time_series(
    tag_ids: Annotated[list[int], Query()] = [],
    device_ids: Annotated[list[int], Query()] = [],
    parent_device_id: int | None = None,
    sensor_type_ids: Annotated[list[int], Query()] = [],
    sensor_type_name_shorts: Annotated[list[str], Query()] = [],
    start: Annotated[
        datetime.datetime | None,
        Depends(filter_start_datetime_or_none_to_date_access_start_time),
    ] = None,
    end: datetime.datetime | None = None,
    project_db: Session = Depends(get_project_db),
    project: models.Project = Depends(get_project_api),
    include_ghost_tags: Annotated[bool, Query()] = False,
    interval: Annotated[str, Query()] = "5min",
):
    """todo

    Args:
        tag_ids: Description for tag_ids.
        device_ids: Description for device_ids.
        parent_device_id: Description for parent_device_id.
        sensor_type_ids: Description for sensor_type_ids.
        sensor_type_name_shorts: Description for sensor_type_name_shorts.
        start: Description for start.
        end: Description for end.
        project_db: Description for project_db.
        project: Description for project.
        include_ghost_tags: Description for include_ghost_tags.
        interval: Description for interval.
    """
    if parent_device_id:
        project_schema = utils.get_project_schema(project_db=project_db)
        devices_df = await core.crud.project.devices.get_project_devices(
            parent_device_ids=[parent_device_id]
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        device_ids_from_parent = devices_df["device_id"].astype(int).tolist()

    else:
        device_ids_from_parent = []

    device_ids = list(set(device_ids + device_ids_from_parent))

    project_schema = utils.get_project_schema(project_db=project_db)
    tags_df = await core.crud.project.tags.get_project_tags_v2(
        tag_ids=tag_ids,
        device_ids=device_ids,
        sensor_type_ids=sensor_type_ids,
        sensor_type_name_shorts=sensor_type_name_shorts,
        name_scada="",
        include_ghost_tags=include_ghost_tags,
    ).get_async(output_type=OutputType.POLARS, schema=project_schema)

    if tags_df is None or tags_df.is_empty():
        raise HTTPException(
            status_code=404,
            detail="No tags configured for this request",
        )
    tags = [SimpleNamespace(**row) for row in tags_df.to_dicts()]

    # If start is None, set to beginning of day
    if start is None:
        start = pd.Timestamp.now(tz=project.time_zone).floor("D")
    else:
        start = pd.Timestamp(start)
        # If start is naive, localize to project time zone
        if start.tzinfo is None:
            start = start.tz_localize(project.time_zone)
        # If start is in different time zone, convert to project time zone
        else:
            start = start.tz_convert(project.time_zone)

    # If end is None, set to end of day
    if end is None:
        end = pd.Timestamp.now(tz=project.time_zone).ceil(interval)
    else:
        end = pd.Timestamp(end)
        # If end is naive, localize to project time zone
        if end.tzinfo is None:
            end = end.tz_localize(project.time_zone)
        # If end is in different time zone, convert to project
        else:
            end = end.tz_convert(project.time_zone)

    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=tags_df,
        query_start=start,
        query_end=end,
        project_db=project_db,
        freq=TimeInterval.FIVE_MINUTES,
    ).get()

    df = data_timeseries_instance.df.to_pandas()
    df = df.set_index("time")
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
    df.columns = df.columns.astype(int)

    tag_id_to_tag_name = await utils.get_tag_id_to_tag_name(
        tags=tags,
    )
    tag_id_to_sensor_type_name = await utils.get_tag_id_to_sensor_type_name(
        tags=tags,
    )
    tag_id_to_device_name_long = await utils.get_tag_id_to_device_name_long(
        project_db,
        tags=tags,
    )
    tag_id_to_tag_name_scada = {tag.tag_id: tag.name_scada for tag in tags}
    tag_id_to_tag_name_long = {tag.tag_id: tag.name_long or "" for tag in tags}
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
            "x": df.index.tz_convert(project.time_zone).tolist(),
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


## This is a temporary endpoint, eventually we will replace the above with
## DataTimeseries.get()
@router.get("/data-timeseries-v3", response_model=list[interfaces.DataTimeSeries])
async def get_timeseries_v3(
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
    tag_ids: Annotated[list[int], Query()] = [],
    sensor_type_ids: Annotated[list[int], Query()] = [],
    start: Annotated[
        datetime.datetime | None,
        Depends(filter_start_datetime_or_none_to_date_access_start_time),
    ] = None,
    end: datetime.datetime | None = None,
    interval: str | None = None,
    ensure_full_range: bool = False,
    cutoff_now: bool = False,
):
    """todo

    Args:
        project_db: Description for project_db.
        operational_db: Description for operational_db.
        project: Description for project.
        tag_ids: Description for tag_ids.
        sensor_type_ids: Description for sensor_type_ids.
        start: Description for start.
        end: Description for end.
        interval: Aggregation step passed to DataTimeseries (e.g. 1min, 5min).
        ensure_full_range: Description for ensure_full_range.
        cutoff_now: Description for cutoff_now.
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
                    f"Invalid interval '{interval}'. Valid intervals are: "
                    f"{valid_options}"
                ),
            ) from exc

    project_schema = utils.get_project_schema(project_db=project_db)
    if tag_ids:
        tags_df = await core.crud.project.tags.get_project_tags_v2(
            tag_ids=tag_ids,
            deep=True,
            include_ghost_tags=True,
        ).get_async(output_type=OutputType.POLARS, schema=project_schema)
    else:
        tags_df = await core.crud.project.tags.get_project_tags_v2(
            sensor_type_ids=sensor_type_ids,
            deep=True,
        ).get_async(output_type=OutputType.POLARS, schema=project_schema)
    if tags_df is None or tags_df.is_empty():
        return []
    tags = [SimpleNamespace(**row) for row in tags_df.to_dicts()]

    data_timeseries_instance = DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=tags_df,
        query_start=start,
        query_end=end,
        project_db=project_db,
        freq=agg_interval,
        ensure_full_range=ensure_full_range,
    )

    data_timeseries = await data_timeseries_instance.get()

    # Convert polars DataFrame to pandas
    df = data_timeseries.df.to_pandas()

    if cutoff_now:
        if "time" in df.columns:
            df = df[df["time"] <= pd.Timestamp.now(tz=project.time_zone)]
        elif "time_bucket" in df.columns:
            df = df[df["time_bucket"] <= pd.Timestamp.now(tz=project.time_zone)]
        else:
            raise ValueError("time or time_bucket column not found in dataframe")

    # Build metadata mappings
    tag_id_to_sensor_type_name = await utils.get_tag_id_to_sensor_type_name(
        tags=tags,
    )
    tag_id_to_device_name_long = await utils.get_tag_id_to_device_name_long(
        project_db,
        tags=tags,
    )
    tag_id_to_tag_name_scada = {tag.tag_id: tag.name_scada for tag in tags}
    tag_id_to_tag_name_long = {tag.tag_id: tag.name_long or "" for tag in tags}
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
        df[data_columns] = df[data_columns].ffill().fillna(0).infer_objects(copy=False)
    elif "time" in df.columns:
        time_col = "time"
        time_series = pd.to_datetime(df[time_col])
        # Apply ffill() then fillna(0) to all columns except time
        data_columns = [col for col in df.columns if col != time_col]
        df[data_columns] = df[data_columns].ffill().fillna(0).infer_objects(copy=False)
    elif "time_bucket" in df.columns:
        time_col = "time_bucket"
        time_series = pd.to_datetime(df[time_col])
        # Apply ffill() then fillna(0) to all columns except time_bucket
        data_columns = [col for col in df.columns if col != time_col]
        df[data_columns] = df[data_columns].ffill().fillna(0).infer_objects(copy=False)
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
        sensor_type_name = tag_id_to_sensor_type_name.get(tag_id, "")
        device_name_long = tag_id_to_device_name_long.get(tag_id, "")
        tag_name_scada = tag_id_to_tag_name_scada.get(tag_id, "")
        tag_name_long = tag_id_to_tag_name_long.get(tag_id, "")
        device_id = tag_id_to_device_id.get(tag_id)
        sensor_type_id = tag_id_to_sensor_type_id.get(tag_id)

        # Get values and convert to list, handling None/NaN
        values = df[col].tolist()
        this_tag = [t for t in tags if t.tag_id == tag_id][0]
        if this_tag.pg_data_type_id == core.enumerations.PGDataType.TEXT:
            y_values = [
                cast(float | str | None, str(val) if pd.notna(val) else None)
                for val in values
            ]
        else:
            y_values = [
                cast(
                    float | str | None,
                    float(val) if pd.notna(val) else None,
                )
                for val in values
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
