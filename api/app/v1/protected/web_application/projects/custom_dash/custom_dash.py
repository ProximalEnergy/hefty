import datetime
import random
import uuid
from typing import Annotated

import numpy as np
import pandas as pd
from core.dependencies import get_db
from core.enumerations import DeviceType, ProjectType, SensorType
from fastapi import APIRouter, Depends, HTTPException, Query
from natsort import natsorted
from pydantic import BaseModel
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
    get_user_dashboards as crud_get_user_dashboards,
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
    component_id: str | int
    component_type: str
    x: int
    y: int
    w: int
    h: int
    config: dict


class CreateDashboardRequest(BaseModel):
    dashboard_name: str
    default_time_range: enumerations.DefaultTimeRange
    default_kpi_time_range: enumerations.DefaultKPITimeRange
    components: list[DashboardComponent]


class UpdateDashboardRequest(BaseModel):
    dashboard_id: uuid.UUID
    dashboard_name: str
    default_time_range: enumerations.DefaultTimeRange
    default_kpi_time_range: enumerations.DefaultKPITimeRange
    components: list[DashboardComponent]


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
    try:
        project_start = pd.Timestamp(start).tz_convert(project.time_zone)
        project_end = pd.Timestamp(end).tz_convert(project.time_zone)
    except Exception:
        project_start = pd.Timestamp(start).tz_localize(project.time_zone)
        project_end = pd.Timestamp(end).tz_localize(project.time_zone)
    sensor_types = core.crud.operational.sensor_types.get_sensor_types(
        db=db,
        sensor_type_ids=[sensor_type_id],
    )
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
            name = (
                sensor_types.find(sensor_type_id=sensor_type_id)[0].name_long + " Mean"
            )
        case "max":
            out = df.max(axis=0)
            name = (
                sensor_types.find(sensor_type_id=sensor_type_id)[0].name_long
                + " Maximum"
            )
        case "min":
            out = df.min(axis=0)
            name = (
                sensor_types.find(sensor_type_id=sensor_type_id)[0].name_long
                + " Minimum"
            )
        case "sum":
            out = df.sum(axis=0)
            name = (
                sensor_types.find(sensor_type_id=sensor_type_id)[0].name_long + " Sum"
            )
        case "median":
            out = df.median(axis=0)
            name = (
                sensor_types.find(sensor_type_id=sensor_type_id)[0].name_long
                + " Median"
            )
        case "std":
            out = df.std(axis=0)
            name = (
                sensor_types.find(sensor_type_id=sensor_type_id)[0].name_long
                + " Standard Deviation"
            )
    devices = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_ids=list(set([t.device_id for t in tags])),
    )
    tag_to_name = (
        tags.pandas_dataframe(index="tag_id")
        .loc[out.index, "device_id"]
        .map(devices.pandas_dataframe(index="device_id")["name_long"])
    )
    out = out.rename(index=tag_to_name.to_dict())
    # Sort by device name using natural sort for consistent ordering
    sorted_indices = natsorted(out.index, key=lambda x: str(x))
    out = out.loc[sorted_indices]
    return {
        "x": out.index.tolist(),
        "y": out.tolist(),
        "sensor_type_id": sensor_type_id,
        "unit": sensor_types.find(sensor_type_id=sensor_type_id)[0].unit,
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
            device = core.crud.project.devices.get_project_devices(
                db=project_db,
                device_type_ids=[DeviceType.PROJECT],
            )
            data_expected = core.crud.project.data_expected.get_project_data_expected(
                project_db=project_db,
                device_ids=[device[0].device_id],
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
):
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
    sensor_types = core.crud.operational.sensor_types.get_sensor_types(
        db=db,
        sensor_type_ids=list(set(sensor_type_ids)),
    ).pandas_dataframe(index="sensor_type_id")
    out = []
    name = ""

    tags = core.crud.project.tags.get_project_tags(
        db=project_db, sensor_type_ids=list(set(sensor_type_ids))
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
    df.loc[pd.Timestamp.now().tz_localize(project.time_zone) :] = np.nan
    for i in range(len(sensor_type_ids)):
        sensor_type_id = sensor_type_ids[i]
        aggregation_type = aggregation_types[i]

        related_tags = tags.find(sensor_type_id=sensor_type_id)
        temp_df = df[df.columns.intersection([t.tag_id for t in related_tags])]  # type: ignore
        sensor_name = str(sensor_types.loc[sensor_type_id, "name_long"])
        match aggregation_type:
            case "none":
                devices = core.crud.project.devices.get_project_devices(
                    db=project_db,
                    device_ids=list(set([t.device_id for t in related_tags])),
                ).pandas_dataframe(index="device_id")
            case "avg":
                # Use skipna=False to ensure NaN is returned when all values are NaN
                temp_df = pd.DataFrame(temp_df.mean(axis=1, skipna=False))
                name = sensor_name + " Mean"
            case "max":
                temp_df = pd.DataFrame(temp_df.max(axis=1, skipna=False))
                name = sensor_name + " Max"
            case "min":
                temp_df = pd.DataFrame(temp_df.min(axis=1, skipna=False))
                name = sensor_name + " Min"
            case "sum":
                # For sum, we need to handle NaN differently since sum() with all NaN returns 0
                # Check if all values in each row are NaN, and if so, return NaN for that row
                all_nan_mask = temp_df.isna().all(axis=1)
                temp_df = pd.DataFrame(temp_df.sum(axis=1, skipna=False))
                temp_df.loc[all_nan_mask] = np.nan
                name = sensor_name + " Sum"
            case "median":
                temp_df = pd.DataFrame(temp_df.median(axis=1, skipna=False))
                name = sensor_name + " Median"
            case "std":
                temp_df = pd.DataFrame(temp_df.std(axis=1, skipna=False))
                name = sensor_name + " Std"
            case "count":
                # Count should return 0 for NaN values, so keep as is
                temp_df = pd.DataFrame(temp_df.count(axis=1))
                name = sensor_name + " Count"
            case _:
                pass
        if sensor_type_id == SensorType.BESS_MV_CIRCUIT_METER_ACTIVE_POWER:
            temp_df *= -1
        for j in range(len(temp_df.columns)):
            if aggregation_type == "none":
                device_name = str(
                    devices.loc[
                        tags.find(tag_id=int(temp_df.columns[j]))[0].device_id,
                        "name_long",
                    ]
                )
                if device_name != "None":
                    name = sensor_name + " " + device_name
                else:
                    name = sensor_name

            out.append(
                {
                    "name": name,
                    "sensor_type_id": sensor_type_id,
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
    MAX_POINTS = 1_000
    try:
        project_start = pd.Timestamp(start).tz_convert(project.time_zone)
        project_end = pd.Timestamp(end).tz_convert(project.time_zone)
    except Exception:
        project_start = pd.Timestamp(start).tz_localize(project.time_zone)
        project_end = pd.Timestamp(end).tz_localize(project.time_zone)
    sensor_types = core.crud.operational.sensor_types.get_sensor_types(
        db=db,
        sensor_type_ids=[x_axis_sensor_type_id, y_axis_sensor_type_id],
    )
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
    return {
        "x": {
            "values": out["x"].tolist(),
            "name": sensor_types.find(sensor_type_id=x_axis_sensor_type_id)[
                0
            ].name_long,
            "unit": sensor_types.find(sensor_type_id=x_axis_sensor_type_id)[0].unit,
        },
        "y": {
            "values": out["y"].tolist(),
            "name": sensor_types.find(sensor_type_id=y_axis_sensor_type_id)[
                0
            ].name_long,
            "unit": sensor_types.find(sensor_type_id=y_axis_sensor_type_id)[0].unit,
        },
    }


@router.get("/user-dashboards")
async def get_user_dashboards(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    user_dashboards = await crud_get_user_dashboards(
        db=db,
        user_id=user.user_id,
        project_id=project.project_id,
    )
    return user_dashboards


@router.post("/create-dashboard")
async def create_user_dashboard(
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    request: CreateDashboardRequest,
):
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


@router.put("/update-dashboard")
async def update_user_dashboard(
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    request: UpdateDashboardRequest,
):
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


@router.delete("/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: str,
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user: Annotated[models.User, Depends(dependencies.get_user_data_async)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
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
