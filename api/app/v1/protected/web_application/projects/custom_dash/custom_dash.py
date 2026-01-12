import datetime
import random
import uuid
from collections import defaultdict
from collections.abc import Iterable
from typing import Annotated, Any

import numpy as np
import pandas as pd
from core.db_query import OutputType
from core.dependencies import get_db
from core.enumerations import DeviceType, ProjectType, SensorType
from fastapi import APIRouter, Depends, HTTPException, Query
from natsort import natsorted
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from app._crud.operational.custom_dashboards import (
    create_user_dashboard as crud_create_user_dashboard,
)
from app._crud.operational.custom_dashboards import (
    delete_user_dashboard as crud_delete_user_dashboard,
)
from app._crud.operational.custom_dashboards import (
    get_dashboard_by_id as crud_get_dashboard_by_id,
)
from app._crud.operational.custom_dashboards import (
    get_dashboard_shared_users as crud_get_dashboard_shared_users,
)
from app._crud.operational.custom_dashboards import (
    get_shared_user_dashboards as crud_get_shared_user_dashboards,
)
from app._crud.operational.custom_dashboards import (
    get_user_dashboards as crud_get_user_dashboards,
)
from app._crud.operational.custom_dashboards import (
    share_user_dashboard as crud_share_user_dashboard,
)
from app._crud.operational.custom_dashboards import (
    unshare_user_dashboard as crud_unshare_user_dashboard,
)
from app._crud.operational.custom_dashboards import (
    update_user_dashboard as crud_update_user_dashboard,
)
from core import enumerations, models

router = APIRouter(
    prefix="/custom-dash",
    tags=["custom-dash"],
    include_in_schema=utils.get_include_in_schema(),
)


class DashboardComponent(BaseModel):
    """todo"""

    component_id: str | int
    component_type: str
    x: int
    y: int
    w: int
    h: int
    config: dict


class CreateDashboardRequest(BaseModel):
    """todo"""

    dashboard_name: str
    default_time_range: enumerations.DefaultTimeRange
    default_kpi_time_range: enumerations.DefaultKPITimeRange
    components: list[DashboardComponent]


class UpdateDashboardRequest(BaseModel):
    """todo"""

    dashboard_id: uuid.UUID
    dashboard_name: str
    default_time_range: enumerations.DefaultTimeRange
    default_kpi_time_range: enumerations.DefaultKPITimeRange
    components: list[DashboardComponent]


class DuplicateDashboardRequest(BaseModel):
    """todo"""

    target_project_ids: list[uuid.UUID] | None = None


class ShareDashboardRequest(BaseModel):
    """todo"""

    shared_user_id: str


@router.get("/bar")
async def get_bar(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    db: Annotated[Session, Depends(get_db)],
    operational_db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    sensor_type_id: int,
    aggregation_type: str,
    start: datetime.datetime,
    end: datetime.datetime,
):
    """todo

    Args:
        project_db: TODO: describe.
        db: TODO: describe.
        operational_db: TODO: describe.
        project: TODO: describe.
        sensor_type_id: TODO: describe.
        aggregation_type: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    try:
        project_start = pd.Timestamp(start).tz_convert(project.time_zone)
        project_end = pd.Timestamp(end).tz_convert(project.time_zone)
    except Exception:
        project_start = pd.Timestamp(start).tz_localize(project.time_zone)
        project_end = pd.Timestamp(end).tz_localize(project.time_zone)
    sensor_types = (
        await core.crud.operational.sensor_types.get_sensor_types(
            sensor_type_ids=[sensor_type_id],
        ).get_async(output_type=OutputType.SQLALCHEMY)
        or []
    )
    sensor_type_map = {
        sensor_type.sensor_type_id: sensor_type for sensor_type in sensor_types
    }
    sensor_type = sensor_type_map.get(sensor_type_id)
    if sensor_type is None:
        raise HTTPException(status_code=404, detail="Sensor type not found")
    tags = core.crud.project.tags.get_project_tags(
        db=project_db,
        sensor_type_ids=[sensor_type_id],
    )
    data_timeseries_v3 = await core.crud.project.data_timeseries.DataTimeseries.get(
        project_name_short=project.name_short,
        tag_ids=[t.tag_id for t in tags],
        query_start=project_start,
        query_end=project_end,
        agg_interval=core.enumerations.TimeInterval.FIVE_MINUTES,
        project_db=project_db,
        operational_db=operational_db,
        return_arrow=False,
    )
    df = data_timeseries_v3.df.to_pandas().set_index("time", drop=True)
    df.columns = df.columns.astype(int)
    df = (
        df.reindex(pd.date_range(project_start, project_end, freq="5min"))
        .ffill()
        .bfill()
    )
    match aggregation_type:
        case "avg" | "mean":
            out = df.mean(axis=0)
            name = sensor_type.name_long + " Mean"
        case "max":
            out = df.max(axis=0)
            name = sensor_type.name_long + " Maximum"
        case "min":
            out = df.min(axis=0)
            name = sensor_type.name_long + " Minimum"
        case "sum":
            out = df.sum(axis=0)
            name = sensor_type.name_long + " Sum"
        case "median":
            out = df.median(axis=0)
            name = sensor_type.name_long + " Median"
        case "std":
            out = df.std(axis=0)
            name = sensor_type.name_long + " Standard Deviation"
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_df = await core.crud.project.devices.get_project_devices(
        device_ids=list(set([t.device_id for t in tags])),
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    devices_df = devices_df.copy()
    devices_df["name_long"] = devices_df["name_long"].fillna("")
    tag_to_name = (
        tags.pandas_dataframe(index="tag_id")
        .loc[out.index, "device_id"]
        .map(devices_df.set_index("device_id")["name_long"])
    )
    out = out.rename(index=tag_to_name.to_dict())
    # Sort by device name using natural sort for consistent ordering
    sorted_indices = natsorted(out.index, key=lambda x: str(x))
    out = out.loc[sorted_indices]
    return {
        "x": out.index.tolist(),
        "y": out.tolist(),
        "sensor_type_id": sensor_type_id,
        "unit": sensor_type.unit,
        "name": name,
    }


@router.get("/gauge")
async def get_gauge(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    db: Annotated[Session, Depends(get_db)],
    operational_db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    measured_variable: str,
    maximum_value: str,
    start: datetime.datetime,
    end: datetime.datetime,
):
    """todo

    Args:
        project_db: TODO: describe.
        db: TODO: describe.
        operational_db: TODO: describe.
        project: TODO: describe.
        measured_variable: TODO: describe.
        maximum_value: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    try:
        project_start = pd.Timestamp(start).tz_convert(project.time_zone)
        project_end = pd.Timestamp(end).tz_convert(project.time_zone)
    except Exception:
        project_start = pd.Timestamp(start).tz_localize(project.time_zone)
        project_end = pd.Timestamp(end).tz_localize(project.time_zone)
    match measured_variable:
        case "meter_actual_power":
            if project.project_type_id == ProjectType.PV:
                measured_sensor_type_id = SensorType.METER_ACTIVE_POWER
            else:
                measured_sensor_type_id = SensorType.BESS_MV_CIRCUIT_METER_ACTIVE_POWER
            tags = core.crud.project.tags.get_project_tags(
                db=project_db,
                sensor_type_ids=[measured_sensor_type_id],
            )
            data_real = await core.crud.project.data_timeseries.DataTimeseries.get(
                project_name_short=project.name_short,
                tag_ids=[t.tag_id for t in tags],
                query_start=project_start,
                query_end=project_end,
                agg_interval=core.enumerations.TimeInterval.FIVE_MINUTES,
                project_db=project_db,
                operational_db=operational_db,
                return_arrow=False,
            )
            df_real = data_real.df.to_pandas().set_index("time", drop=True)
            df_real.columns = df_real.columns.astype(int)
            series_real = df_real.sum(axis=1)
    series_expected = None
    match maximum_value:
        case "expected_energy":
            metrics_priority_order = [12, 11, 6, 5]
            project_schema = utils.get_project_schema(project_db=project_db)
            device_df = await core.crud.project.devices.get_project_devices(
                device_type_ids=[DeviceType.PROJECT],
            ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
            data_expected = core.crud.project.data_expected.get_project_data_expected(
                project_db=project_db,
                device_ids=[int(device_df["device_id"].iloc[0])],
                start=start,
                end=end,
            )
            df_expected = data_expected.pandas_dataframe(
                index="time", as_datetime=True, tz=project.time_zone
            )
            if not df_expected.empty:
                for metric_id in metrics_priority_order:
                    df_exp_temp = df_expected[
                        df_expected["expected_metric_id"] == metric_id
                    ].copy()
                    if df_exp_temp.empty:
                        continue
                    df_expected = df_exp_temp.copy().sort_index()
                    series_expected = df_expected["value"] / 1_000_000
                    series_expected = series_expected.reindex_like(series_real).fillna(
                        0
                    )
                    break
        case "contract_capacity":
            pass
    if series_expected is None:
        return {
            "value": 0,
            "value_raw": series_real.sum() * 5 / 60,
            "max": 0,
        }
    return {
        "value": series_real.sum() / series_expected.sum() * 100,
        "value_raw": series_real.sum() * 5 / 60,
        "max": series_expected.sum() * 5 / 60,
    }


@router.get("/line")
async def get_line(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    db: Annotated[Session, Depends(get_db)],
    operational_db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    sensor_type_ids: Annotated[list[int], Query()],
    aggregation_types: Annotated[list[str], Query()],
    start: datetime.datetime,
    end: datetime.datetime,
    tag_ids: Annotated[list[str] | None, Query()] = None,
    maximum: Annotated[list[str] | None, Query()] = None,
    minimum: Annotated[list[str] | None, Query()] = None,
):
    """todo

    Args:
        project_db: TODO: describe.
        db: TODO: describe.
        operational_db: TODO: describe.
        project: TODO: describe.
        sensor_type_ids: TODO: describe.
        aggregation_types: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        tag_ids: TODO: describe.
        maximum: TODO: describe.
        minimum: TODO: describe.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    # --- Time handling (unchanged) ---
    try:
        project_start = pd.Timestamp(start).tz_convert(project.time_zone)
        project_end = pd.Timestamp(end).tz_convert(project.time_zone)
    except Exception:
        project_start = pd.Timestamp(start).tz_localize(project.time_zone)
        project_end = pd.Timestamp(end).tz_localize(project.time_zone)

    if len(sensor_type_ids) != len(aggregation_types):
        raise HTTPException(
            status_code=400,
            detail="sensor_type_ids and aggregation_types must have the same length",
        )

    # --- Parse maximum and minimum from strings to floats ---
    parsed_maximum: list[float | None] | None = None
    if maximum is not None:
        parsed_maximum = []
        for max_val in maximum:
            if max_val is None or max_val == "":
                parsed_maximum.append(None)
            else:
                try:
                    parsed_maximum.append(float(max_val))
                except (ValueError, TypeError):
                    parsed_maximum.append(None)

    parsed_minimum: list[float | None] | None = None
    if minimum is not None:
        parsed_minimum = []
        for min_val in minimum:
            if min_val is None or min_val == "":
                parsed_minimum.append(None)
            else:
                try:
                    parsed_minimum.append(float(min_val))
                except (ValueError, TypeError):
                    parsed_minimum.append(None)

    # --- Parse tag_ids into list[list[int]] aligned with traces ---
    parsed_tag_ids: list[list[int]] | None = None
    if tag_ids is not None:
        if len(tag_ids) != len(sensor_type_ids):
            raise HTTPException(
                status_code=400,
                detail=(
                    "tag_ids must have the same length as sensor_type_ids and "
                    "aggregation_types (use an empty string for traces that do not "
                    "specify tag_ids)."
                ),
            )
        parsed_tag_ids = []
        for tag_id_str in tag_ids:
            if tag_id_str:
                parsed_tag_ids.append(
                    [int(tid) for tid in tag_id_str.split(",") if tid.strip()]
                )
            else:
                parsed_tag_ids.append([])

    # --- Basic validation of aggregation_types vs tag_ids rule ---
    if parsed_tag_ids is not None:
        for agg_type, trace_tag_ids in zip(aggregation_types, parsed_tag_ids):
            # If tag_ids are provided for a trace, aggregation_type must be "none"
            if trace_tag_ids and agg_type != "none":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "If tag_ids are passed for a trace, aggregation_type "
                        "must be 'none'."
                    ),
                )

    # --- Load sensor type metadata (unchanged) ---
    sensor_types = await core.crud.operational.sensor_types.get_sensor_types(
        sensor_type_ids=list(set(sensor_type_ids)),
    ).get_async(output_type=OutputType.PANDAS)

    if not sensor_types.empty:
        sensor_types = sensor_types.set_index("sensor_type_id").sort_index()
    else:
        sensor_types = pd.DataFrame(
            columns=["name_long", "unit"],
            index=pd.Index([], name="sensor_type_id"),
        )

    # ------------------------------------------------------------------
    # Decide which tags to pull:
    #   - For some sensor types we need *all* tags (aggregations or "no tag limit").
    #   - For others we only need explicitly listed tag_ids.
    # ------------------------------------------------------------------
    sensor_type_ids_need_all: set[int] = set()
    specific_tag_ids_by_sensor_type: dict[int, set[int]] = defaultdict(set)

    # Case 1: no tag_ids at all -> old behavior: all tags for all sensor types
    if parsed_tag_ids is None:
        sensor_type_ids_need_all = set(sensor_type_ids)
    else:
        # Case 2: tag_ids provided -> per-trace logic
        for st_id, agg_type, trace_tag_ids in zip(
            sensor_type_ids, aggregation_types, parsed_tag_ids
        ):
            if agg_type != "none":
                # Any aggregation across a sensor type requires all tags of that type
                sensor_type_ids_need_all.add(st_id)
            else:
                if trace_tag_ids:
                    # This trace only needs a subset for this sensor_type
                    specific_tag_ids_by_sensor_type[st_id].update(trace_tag_ids)
                else:
                    # agg_type == "none" but no tag_ids given => treat as "all tags"
                    sensor_type_ids_need_all.add(st_id)

        # If a sensor_type needs all tags, we don't need to track its specific subset
        for st_id in list(specific_tag_ids_by_sensor_type.keys()):
            if st_id in sensor_type_ids_need_all:
                specific_tag_ids_by_sensor_type.pop(st_id, None)

    # ------------------------------------------------------------------
    # Pull tags from DB efficiently
    # ------------------------------------------------------------------
    # Helper: merge tag collections into a simple list while deduplicating by tag_id
    def merge_tag_lists(*tag_lists: Iterable[Any]) -> list[Any]:
        seen_tag_ids: set[int] = set()
        merged: list[Any] = []
        for lst in tag_lists:
            for t in lst:
                tid = int(t.tag_id)
                if tid not in seen_tag_ids:
                    seen_tag_ids.add(tid)
                    merged.append(t)
        return merged

    # 1) Tags for sensor types that require *all* tags
    tags_all: list[Any] = []
    if sensor_type_ids_need_all:
        tags_all = list(
            core.crud.project.tags.get_project_tags(
                db=project_db,
                sensor_type_ids=list(sensor_type_ids_need_all),
            )
        )

    # 2) Tags that are explicitly requested by id for other sensor types
    tags_specific: list[Any] = []
    if specific_tag_ids_by_sensor_type:
        flat_specific_tag_ids = sorted(
            {tid for tids in specific_tag_ids_by_sensor_type.values() for tid in tids}
        )
        if flat_specific_tag_ids:
            tags_specific = list(
                core.crud.project.tags.get_project_tags(
                    db=project_db,
                    tag_ids=flat_specific_tag_ids,
                )
            )

    # Combined list of all tags we actually need
    tags: list[Any] = merge_tag_lists(tags_all, tags_specific)

    if not tags:
        # No tags resolved -> return empty response
        return []

    # Small helpers for tag lookup since we no longer rely on tags.find()
    def tags_for_sensor_type(*, st_id: int) -> list[Any]:
        """Get all tags for a sensor type.

        Args:
            st_id: TODO: describe.
        """
        return [t for t in tags if int(t.sensor_type_id) == int(st_id)]

    def tag_by_id(*, tag_id: int) -> Any:
        """Get a tag by its ID.

        Args:
            tag_id: TODO: describe.
        """
        for t in tags:
            if int(t.tag_id) == int(tag_id):
                return t
        return None

    # ------------------------------------------------------------------
    # Pull timeseries data for *only* the tags we fetched
    # ------------------------------------------------------------------
    tag_ids_for_timeseries = [int(t.tag_id) for t in tags]

    data_timeseries_v3 = await core.crud.project.data_timeseries.DataTimeseries.get(
        project_name_short=project.name_short,
        tag_ids=tag_ids_for_timeseries,
        query_start=project_start,
        query_end=project_end,
        agg_interval=core.enumerations.TimeInterval.FIVE_MINUTES,
        project_db=project_db,
        operational_db=operational_db,
        return_arrow=False,
    )

    df = data_timeseries_v3.df.to_pandas().set_index("time", drop=True)
    df.columns = df.columns.astype(int)

    # Reindex to a perfect 5-minute grid and forward/backward fill
    df = (
        df.reindex(pd.date_range(project_start, project_end, freq="5min"))
        .ffill()
        .bfill()
    )

    # Blank out future values
    df.loc[pd.Timestamp.now().tz_localize(project.time_zone) :] = np.nan

    out: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Build traces
    # ------------------------------------------------------------------
    for i, (sensor_type_id, aggregation_type) in enumerate(
        zip(sensor_type_ids, aggregation_types)
    ):
        # Base tags for this sensor type
        related_tags = tags_for_sensor_type(st_id=sensor_type_id)

        # If this trace has specific tag_ids, restrict to those
        if parsed_tag_ids is not None:
            trace_tag_ids = parsed_tag_ids[i]
            if trace_tag_ids:
                trace_tag_id_set = set(trace_tag_ids)
                related_tags = [
                    t for t in related_tags if int(t.tag_id) in trace_tag_id_set
                ]

        if not related_tags:
            # Nothing to plot for this trace
            continue

        # Restrict the dataframe columns to the tags for this trace
        trace_tag_ids_int = [int(t.tag_id) for t in related_tags]
        # Filter columns to only include the tag IDs for this trace
        # Use list comprehension to filter columns since intersection has type issues
        available_tag_ids = [col for col in df.columns if col in trace_tag_ids_int]
        temp_df = df[available_tag_ids]

        sensor_name = str(sensor_types.loc[sensor_type_id, "name_long"])
        name = sensor_name  # default; may be overridden below

        # Aggregation behavior
        match aggregation_type:
            case "none":
                # For "none", we keep one column per tag; need device names
                devices_df = await core.crud.project.devices.get_project_devices(
                    device_ids=list({int(t.device_id) for t in related_tags}),
                ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
                devices_df = devices_df.copy()
                devices_df["name_long"] = devices_df["name_long"].fillna("")
                devices_df = devices_df.set_index("device_id")
            case "avg":
                temp_df = pd.DataFrame(temp_df.mean(axis=1))
                name = sensor_name + " Mean"
            case "max":
                temp_df = pd.DataFrame(temp_df.max(axis=1))
                name = sensor_name + " Max"
            case "min":
                temp_df = pd.DataFrame(temp_df.min(axis=1))
                name = sensor_name + " Min"
            case "sum":
                # Maintain NaN where *all* values were NaN
                all_nan_mask = temp_df.isna().all(axis=1)
                temp_df = pd.DataFrame(temp_df.sum(axis=1))
                temp_df.loc[all_nan_mask] = np.nan
                name = sensor_name + " Sum"
            case "median":
                temp_df = pd.DataFrame(temp_df.median(axis=1))
                name = sensor_name + " Median"
            case "std":
                temp_df = pd.DataFrame(temp_df.std(axis=1))
                name = sensor_name + " Std"
            case "count":
                temp_df = pd.DataFrame(temp_df.count(axis=1))
                name = sensor_name + " Count"
            case _:
                # Unknown aggregation_type: leave as-is (one column per tag)
                pass

        # Special handling for this sensor type
        if sensor_type_id == SensorType.BESS_MV_CIRCUIT_METER_ACTIVE_POWER:
            temp_df *= -1

        # Get maximum and minimum for this trace (index i)
        trace_maximum = None
        trace_minimum = None
        if parsed_maximum is not None and i < len(parsed_maximum):
            trace_maximum = parsed_maximum[i]
        if parsed_minimum is not None and i < len(parsed_minimum):
            trace_minimum = parsed_minimum[i]

        # Build output traces
        for j, col in enumerate(temp_df.columns):
            trace_name = name
            if aggregation_type == "none":
                tag = tag_by_id(tag_id=int(col))
                if not tag:
                    continue
                device_name = str(devices_df.loc[int(tag.device_id), "name_long"])
                if device_name != "None":
                    trace_name = f"{sensor_name} {device_name}"
                else:
                    trace_name = sensor_name

            out.append(
                {
                    "name": trace_name,
                    "sensor_type_id": sensor_type_id,
                    "maximum": trace_maximum,
                    "minimum": trace_minimum,
                    "x": temp_df.index.tolist(),
                    "y": temp_df.iloc[:, j].replace(np.nan, None).tolist(),
                    "unit": sensor_types.loc[sensor_type_id, "unit"],
                }
            )

    return out


@router.get("/scatter")
async def get_scatter(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    db: Annotated[Session, Depends(get_db)],
    operational_db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    x_axis_sensor_type_id: int,
    y_axis_sensor_type_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
):
    """todo

    Args:
        project_db: TODO: describe.
        db: TODO: describe.
        operational_db: TODO: describe.
        project: TODO: describe.
        x_axis_sensor_type_id: TODO: describe.
        y_axis_sensor_type_id: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    MAX_POINTS = 1_000
    try:
        project_start = pd.Timestamp(start).tz_convert(project.time_zone)
        project_end = pd.Timestamp(end).tz_convert(project.time_zone)
    except Exception:
        project_start = pd.Timestamp(start).tz_localize(project.time_zone)
        project_end = pd.Timestamp(end).tz_localize(project.time_zone)
    sensor_types = (
        await core.crud.operational.sensor_types.get_sensor_types(
            sensor_type_ids=[x_axis_sensor_type_id, y_axis_sensor_type_id],
        ).get_async(output_type=OutputType.SQLALCHEMY)
        or []
    )
    sensor_type_map = {
        sensor_type.sensor_type_id: sensor_type for sensor_type in sensor_types
    }
    tags = core.crud.project.tags.get_project_tags(
        db=project_db,
        sensor_type_ids=[x_axis_sensor_type_id, y_axis_sensor_type_id],
    )
    x_axis_tags = tags.find(sensor_type_id=x_axis_sensor_type_id)
    y_axis_tags = tags.find(sensor_type_id=y_axis_sensor_type_id)
    if len(x_axis_tags) > 100:
        x_axis_tags = x_axis_tags.find(
            tag_id__in=random.sample([t.tag_id for t in x_axis_tags], 100)
        )
    if len(y_axis_tags) > 100:
        y_axis_tags = y_axis_tags.find(
            tag_id__in=random.sample([t.tag_id for t in y_axis_tags], 100)
        )
    x_axis_tag_ids = [t.tag_id for t in x_axis_tags]
    y_axis_tag_ids = [t.tag_id for t in y_axis_tags]
    tags = tags.find(tag_id__in=x_axis_tag_ids + y_axis_tag_ids)

    data_timeseries_v3 = await core.crud.project.data_timeseries.DataTimeseries.get(
        project_name_short=project.name_short,
        tag_ids=[t.tag_id for t in tags],
        query_start=project_start,
        query_end=project_end,
        agg_interval=core.enumerations.TimeInterval.FIVE_MINUTES,
        project_db=project_db,
        operational_db=operational_db,
        return_arrow=False,
    )
    df = data_timeseries_v3.df.to_pandas().set_index("time", drop=True)
    df.columns = df.columns.astype(int)
    x_axis_df = df[
        df.columns.astype(int).intersection([tag_id for tag_id in x_axis_tag_ids])
    ]
    y_axis_df = df[
        df.columns.astype(int).intersection([tag_id for tag_id in y_axis_tag_ids])
    ]

    # 1) Align indices (keep only timestamps present in both)
    idx = x_axis_df.index.intersection(y_axis_df.index)
    X = x_axis_df.loc[idx]
    Y = y_axis_df.loc[idx]

    # 2) Long-form each side (preserve NaNs for optional filtering later)
    x_long = (
        X.stack(future_stack=True)
        .reset_index()
        .rename(columns={"time": "timestamp", "level_1": "x_col", 0: "x"})
    )
    y_long = (
        Y.stack(future_stack=True)
        .reset_index()
        .rename(columns={"time": "timestamp", "level_1": "y_col", 0: "y"})
    )

    # after the merge; keep timestamp for stratification
    tmp = x_long.merge(y_long, on="timestamp", how="inner")[["timestamp", "x", "y"]]
    tmp = tmp.dropna(subset=["x", "y"]).round(3).drop_duplicates()

    k = max(1, int(MAX_POINTS / max(1, tmp["timestamp"].nunique())))
    tmp = tmp.groupby("timestamp", group_keys=False)[["x", "y"]].apply(
        lambda group: group.sample(n=min(k, len(group)))
    )

    out = tmp[["x", "y"]].reset_index(drop=True)
    x_sensor_type = sensor_type_map.get(x_axis_sensor_type_id)
    y_sensor_type = sensor_type_map.get(y_axis_sensor_type_id)

    if not x_sensor_type or not y_sensor_type:
        raise HTTPException(
            status_code=404,
            detail="One or more sensor types not found",
        )

    return {
        "x": {
            "values": out["x"].tolist(),
            "name": x_sensor_type.name_long,
            "unit": x_sensor_type.unit,
        },
        "y": {
            "values": out["y"].tolist(),
            "name": y_sensor_type.name_long,
            "unit": y_sensor_type.unit,
        },
    }


@router.get("/user-dashboards")
async def get_user_dashboards(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    """todo

    Args:
        db: TODO: describe.
        user: TODO: describe.
        project: TODO: describe.
    """
    user_dashboards = await crud_get_user_dashboards(
        db=db,
        user_id=user.user_id,
        project_id=project.project_id,
    )
    return user_dashboards


@router.get("/shared-user-dashboards")
async def get_shared_user_dashboards(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    """todo

    Args:
        db: TODO: describe.
        user: TODO: describe.
        project: TODO: describe.
    """
    shared_user_dashboards = await crud_get_shared_user_dashboards(
        db=db,
        user_id=user.user_id,
        project_id=project.project_id,
    )
    return shared_user_dashboards


@router.post("/create-dashboard")
async def create_user_dashboard(
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    request: CreateDashboardRequest,
):
    """todo

    Args:
        db: TODO: describe.
        user: TODO: describe.
        project: TODO: describe.
        request: TODO: describe.
    """
    new_dashboard = await crud_create_user_dashboard(
        db=db,
        owner_user_id=user.user_id,
        project_id=project.project_id,
        dashboard_name=request.dashboard_name,
        default_time_range=request.default_time_range,
        default_kpi_time_range=request.default_kpi_time_range,
        components=request.components,
    )
    return {"dashboard_id": new_dashboard.dashboard_id}


@router.post("/duplicate/{dashboard_id}")
async def duplicate_user_dashboard(
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    dashboard_id: str,
    request: DuplicateDashboardRequest | None = None,
):
    """todo

    Args:
        db: TODO: describe.
        user: TODO: describe.
        project: TODO: describe.
        dashboard_id: TODO: describe.
        request: TODO: describe.
    """
    try:
        dashboard_uuid = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")

    try:
        original_dashboard = await crud_get_dashboard_by_id(
            db=db,
            dashboard_id=dashboard_uuid,
            user_id=user.user_id,
            project_id=project.project_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Determine target project IDs
    target_project_ids = (
        request.target_project_ids
        if request and request.target_project_ids
        else [project.project_id]
    )

    def process_components_for_project(
        *,
        target_project_id: uuid.UUID,
    ) -> list[DashboardComponent]:
        """Process components, replacing tag IDs with -1 if duplicating to a
        different project.

        Args:
            target_project_id: TODO: describe.
        """
        processed_components = []
        is_different_project = target_project_id != project.project_id

        for component in original_dashboard["components"]:
            component_dict = dict(component)
            config = component_dict.get("config", {})

            if is_different_project and component_dict.get("component_type") == "line":
                # For line components, replace tag IDs in traces with -1
                if "traces" in config and isinstance(config["traces"], list):
                    processed_traces = []
                    for trace in config["traces"]:
                        processed_trace = dict(trace)
                        if "tagIds" in processed_trace and isinstance(
                            processed_trace["tagIds"], list
                        ):
                            # Replace all tag IDs with -1 placeholder
                            # (only if there are actual tag IDs, not if already empty)
                            if processed_trace["tagIds"]:
                                processed_trace["tagIds"] = [-1]
                        processed_traces.append(processed_trace)
                    config = {**config, "traces": processed_traces}
                    component_dict["config"] = config

            processed_components.append(component_dict)

        # Convert processed component dictionaries to Pydantic models
        return [DashboardComponent(**component) for component in processed_components]

    # Verify user has access to all target projects
    for target_project_id in target_project_ids:
        # Check if user has access to this project
        project_query = select(models.Project).where(
            models.Project.project_id == target_project_id
        )
        project_result = await db.execute(project_query)
        target_project = project_result.scalar_one_or_none()

        if not target_project:
            raise HTTPException(
                status_code=404,
                detail=f"Project {target_project_id} not found",
            )

        # Check user project access
        user_project_query = select(models.UserProject).where(
            models.UserProject.user_id == user.user_id,
            models.UserProject.operational_project_id == target_project_id,
        )
        user_project_result = await db.execute(user_project_query)
        user_project = user_project_result.scalar_one_or_none()

        if not user_project:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to project {target_project_id}",
            )

    # Create dashboards in all target projects
    created_dashboard_ids = []
    for target_project_id in target_project_ids:
        # Process components for this specific target project
        component_models = process_components_for_project(
            target_project_id=target_project_id
        )

        new_dashboard = await crud_create_user_dashboard(
            db=db,
            owner_user_id=user.user_id,
            project_id=target_project_id,
            dashboard_name=f"Copy of {original_dashboard['dashboard_name']}",
            default_time_range=original_dashboard["default_time_range"],
            default_kpi_time_range=original_dashboard["default_kpi_time_range"],
            components=component_models,
        )
        created_dashboard_ids.append(new_dashboard.dashboard_id)

    # Return the first dashboard ID for backward compatibility, and all IDs
    return {
        "dashboard_id": created_dashboard_ids[0] if created_dashboard_ids else None,
        "dashboard_ids": created_dashboard_ids,
    }


@router.put("/update-dashboard")
async def update_user_dashboard(
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    request: UpdateDashboardRequest,
):
    """todo

    Args:
        db: TODO: describe.
        user: TODO: describe.
        project: TODO: describe.
        request: TODO: describe.
    """
    try:
        updated_dashboard = await crud_update_user_dashboard(
            db=db,
            dashboard_id=request.dashboard_id,
            owner_user_id=user.user_id,
            project_id=project.project_id,
            dashboard_name=request.dashboard_name,
            default_time_range=request.default_time_range,
            default_kpi_time_range=request.default_kpi_time_range,
            components=request.components,
        )
        return {"dashboard_id": updated_dashboard.dashboard_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{dashboard_id}")
async def get_dashboard(
    dashboard_id: str,
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    """todo

    Args:
        dashboard_id: TODO: describe.
        db: TODO: describe.
        user: TODO: describe.
        project: TODO: describe.
    """
    try:
        dashboard_uuid = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")

    try:
        dashboard = await crud_get_dashboard_by_id(
            db=db,
            dashboard_id=dashboard_uuid,
            user_id=user.user_id,
            project_id=project.project_id,
        )
        return dashboard
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/share/{dashboard_id}/users")
async def get_dashboard_shared_users_endpoint(
    dashboard_id: str,
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    """Get all users who have share access to a dashboard.

    Args:
        db: TODO: describe.
        user: TODO: describe.
        project: TODO: describe.
        dashboard_id: TODO: describe.
    """
    try:
        dashboard_uuid = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")

    try:
        shared_user_ids = await crud_get_dashboard_shared_users(
            db=db,
            dashboard_id=dashboard_uuid,
            owner_user_id=user.user_id,
            project_id=project.project_id,
        )
        return {"shared_user_ids": shared_user_ids}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/share/{dashboard_id}")
async def share_dashboard(
    dashboard_id: str,
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    request: ShareDashboardRequest,
):
    """todo

    Args:
        db: TODO: describe.
        user: TODO: describe.
        project: TODO: describe.
        dashboard_id: TODO: describe.
        request: TODO: describe.
    """
    try:
        dashboard_uuid = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")

    try:
        shared_dashboard = await crud_share_user_dashboard(
            db=db,
            dashboard_id=dashboard_uuid,
            owner_user_id=user.user_id,
            shared_user_id=request.shared_user_id,
            project_id=project.project_id,
        )
        return shared_dashboard
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/share/{dashboard_id}")
async def unshare_dashboard(
    dashboard_id: str,
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    request: ShareDashboardRequest,
):
    """Unshare a dashboard with a user.

    Args:
        db: TODO: describe.
        user: TODO: describe.
        project: TODO: describe.
        dashboard_id: TODO: describe.
        request: TODO: describe.
    """
    try:
        dashboard_uuid = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")

    try:
        unshared_dashboard = await crud_unshare_user_dashboard(
            db=db,
            dashboard_id=dashboard_uuid,
            owner_user_id=user.user_id,
            shared_user_id=request.shared_user_id,
            project_id=project.project_id,
        )
        return unshared_dashboard
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: str,
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    """todo

    Args:
        dashboard_id: TODO: describe.
        db: TODO: describe.
        user: TODO: describe.
        project: TODO: describe.
    """
    try:
        dashboard_uuid = uuid.UUID(dashboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")

    try:
        result = await crud_delete_user_dashboard(
            db=db,
            dashboard_id=dashboard_uuid,
            owner_user_id=user.user_id,
            project_id=project.project_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
