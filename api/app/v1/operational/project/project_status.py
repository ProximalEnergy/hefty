import datetime
import string
from typing import Annotated, Any, Literal

import pandas as pd
from core.db_query import OutputType
from core.enumerations import SensorTypeEnum
from fastapi import APIRouter, Depends, HTTPException, Query
from natsort import natsorted
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app._dependencies.filtering import filter_start_datetime_to_data_access_start_time
from app.dependencies import get_project_api, get_project_db
from app.logger import logger
from core import models

DESCRIPTION_404 = "Status not found"

router = APIRouter(
    prefix="/status",
    tags=["project_status"],
)

# Cache translation table outside the endpoint
delete_chars = string.punctuation + string.whitespace
tbl = str.maketrans("", "", delete_chars)


class StatusTimeSeries(BaseModel):
    """todo"""

    x: list[datetime.datetime]
    y: list[str | None]
    name: str
    alert: list[bool]
    tag_id: int


class StatusEntry(BaseModel):
    """A single status entry for a device."""

    time: datetime.datetime
    status: str
    status_type: Literal["nominal", "warning", "alert"]


class DeviceStatus(BaseModel):
    """A device and its statuses."""

    device_id: int | None
    statuses: list[StatusEntry]


# -- unchanged interpret wrapper --
@router.get("/interpret")
async def interpret(
    db: Annotated[Session, Depends(get_project_db)],
    *,
    status_tags: Annotated[list[int], Query()] = [],
    status_values: Annotated[list[Any], Query()] = [],
):
    """todo

    Args:
        db: Description for db.
        status_tags: Description for status_tags.
        status_values: Description for status_values.
    """
    try:
        return await core.crud.project.statuses.get_status_interpret(
            db=db,
            status_tags=status_tags,
            status_values=status_values,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -- time-series endpoint for Python --
@router.get("/time-series-python", deprecated=True)
async def get_status_time_series_python(
    db: Annotated[  # noqa: ARG001
        AsyncSession,
        Depends(core.database.get_db_async),
    ],
    *,
    project: Annotated[models.Project, Depends(get_project_api)],
    project_db: Annotated[Session, Depends(get_project_db)],
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: list[int] | None = Query(None),
    tag_ids: list[int] | None = Query(None),
    device_type_ids: list[int] | None = Query(None),
    sensor_types: list[SensorTypeEnum] | None = None,
):
    """todo

    Args:
        db: Description for db.
        project: Description for project.
        project_db: Description for project_db.
        start: Description for start.
        end: Description for end.
        device_ids: Description for device_ids.
        tag_ids: Description for tag_ids.
        device_type_ids: Description for device_type_ids.
        sensor_types: Description for sensor_types.
    """
    logger.warning(
        "/projects/{project_id}/status/time-series-python is deprecated; "
        "call core.domain.statuses.statuses.get_status_time_series_failure_mode_ids "
        "instead.",
    )
    if sensor_types is not None:
        sensor_type_ids = SensorTypeEnum.extract_values(enum_list=sensor_types)
    else:
        sensor_type_ids = None
    data = await core.domain.statuses.statuses.get_status_time_series_failure_mode_ids(
        project_db=project_db,
        project=project,
        sensor_type_ids=sensor_type_ids,
        start=start,
        end=end,
        device_ids=device_ids,
        tag_ids=tag_ids,
        device_type_ids=device_type_ids,
    )
    return data


@router.get("/last-known-statuses", response_model=list[DeviceStatus])
async def get_last_known_statuses_route(
    *,
    project: Annotated[models.Project, Depends(get_project_api)],
    device_type_ids: list[int] | None = Query(None),
    sensor_type_ids: list[int] | None = Query(None),
    tag_ids: list[int] | None = Query(None),
    device_ids: list[int] | None = Query(None),
    alert_only: bool = Query(True),
):
    """
    Returns the human-readable interpretation of
    last known status values for the project.
    Returns data in the form:
    [
        {
            "device_id": ...,
            "statuses": [
                {"time": "...", "status": "...", "status_type": "..."},
                {"time": "...", "status": "...", "status_type": "..."},
                ...
            ],
        },
        {
            "device_id": ...,
            "statuses": [
                {"time": "...", "status": "...", "status_type": "..."},
                {"time": "...", "status": "...", "status_type": "..."},
                ...
            ],
        },
    ]

    Args:
        project: The project to get statuses for.
        device_type_ids: List of device type IDs to filter statuses by.
        If None, all device types will be included.
        sensor_type_ids: List of sensor type IDs to filter statuses by.
        If None, all sensor types will be included.
        tag_ids: List of individual tag IDs to filter statuses by.
        If None, all tags will be included.
        device_ids: List of individual device IDs to filter statuses by.
        If None, all devices will be included.
        alert_only: If True, only return statuses that are in alert (non-nominal) state.
        If False, return all statuses. WARNING: False may return a lot of data.
    """
    data = await core.crud.project.statuses.get_last_known_statuses(
        project=project,
        device_type_ids=device_type_ids,
        sensor_type_ids=sensor_type_ids,
        tag_ids=tag_ids,
        device_ids=device_ids,
        alert_only=alert_only,
    )
    return data


@router.get("/time-series-js", response_model=list[StatusTimeSeries])
async def get_status_time_series_js(
    *,
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
    device_ids: list[int] = Query(...),
    start: Annotated[
        datetime.datetime, Depends(filter_start_datetime_to_data_access_start_time)
    ],
    end: datetime.datetime,
):
    """
    Returns the time series of statuses for the project, optimized for frontend display.
    Returns data in the form:
    [
        {
            "x": ...,
            "y": ...,
            "name": ...,
            "alert": ...,
            "tag_id": ...,
        },
    ]

    Args:
        project_db: The project database session.
        project: The project to get statuses for.
        device_ids: List of device IDs to filter statuses by.
        start: The start time to get statuses for.
        end: The end time to get statuses for.
    """
    get_status_tags_query = core.crud.project.statuses.get_status_tags(
        device_ids=device_ids,
    )
    tag_ids = (
        (
            await get_status_tags_query.get_async(
                schema=project.name_short, output_type=OutputType.PANDAS
            )
        )["tag_id"]
        .unique()
        .tolist()
    )
    if len(tag_ids) == 0:
        return []
    data = await core.domain.statuses.statuses.get_status_timeseries_interpreted(
        project_db=project_db,
        project=project,
        tag_ids=tag_ids,
        start=start,
        end=end,
    )
    status_names = await core.crud.project.statuses.get_status_name_from_tag_id(
        tag_ids=tag_ids,
    ).get_async(output_type=OutputType.PANDAS, schema=project.name_short)
    status_names = status_names.set_index("tag_id")
    facts = pd.DataFrame(data)
    timeline_index = pd.date_range(start, end, freq="5min")
    if facts.empty or "is_nominal" not in facts.columns:
        alerts_df = pd.DataFrame(False, index=timeline_index, columns=tag_ids)
        wide_reindexed = pd.DataFrame(index=timeline_index, columns=tag_ids)
    else:
        alerts = ~facts["is_nominal"].astype(bool)
        alerts_df = (
            alerts.groupby([facts["time"], facts["tag_id"]])
            .any()
            .unstack("tag_id")
            .reindex(
                index=timeline_index,
                columns=tag_ids,
            )
        ).fillna(False)
        labels = (
            facts["description"].astype("string")
            + ": "
            + (facts["resolved_state"].combine_first(facts["observed_bool"])).astype(
                "string"
            )
        )
        cell_text = labels.groupby([facts["time"], facts["tag_id"]]).agg(", ".join)
        wide = cell_text.unstack("tag_id")
        wide_reindexed = wide.reindex(
            index=timeline_index,
            columns=tag_ids,
        )
    data_out = [
        {
            "x": pd.to_datetime(wide_reindexed.index)
            .tz_convert(project.time_zone)
            .tolist(),
            "y": wide_reindexed[col].fillna("Nominal").tolist(),
            "name": status_names.loc[col, "name_long"],
            "alert": alerts_df[col].tolist(),
            "tag_id": col,
        }
        for col in wide_reindexed.columns
    ]
    return natsorted(data_out, key=lambda item: str(item["name"] or ""))
