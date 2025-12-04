import datetime
import string
from typing import Annotated, Any

import numpy as np
import pandas as pd
from core.enumerations import SensorType
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app.dependencies import get_project_api, get_project_db
from core import models

DESCRIPTION_404 = "Status not found"

router = APIRouter(prefix="/projects/{project_id}/status", tags=["project_status"])

# Cache translation table outside the endpoint
delete_chars = string.punctuation + string.whitespace
tbl = str.maketrans("", "", delete_chars)


def strtobool(val: str) -> int:  # skip-star-syntax
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError(f"invalid truth value {val!r}")


# -- unchanged interpret wrapper --
@router.get("/interpret")
def interpret(
    db: Annotated[Session, Depends(get_project_db)],
    *,
    status_tags: Annotated[list[int], Query()] = [],
    status_values: Annotated[list[Any], Query()] = [],
):
    try:
        return core.crud.project.statuses.get_status_interpret(
            db=db,
            status_tags=status_tags,
            status_values=status_values,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -- optimized /time-series endpoint for JS --
@router.get("/time-series")
def get_status_time_series(
    db: Annotated[Session, Depends(get_project_db)],
    *,
    project: Annotated[models.Project, Depends(get_project_api)],
    project_db: Annotated[Session, Depends(get_project_db)],
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: list[int] | None = Query(None),
    tag_ids: list[int] | None = Query(None),
):
    status_sensor_type_ids = [
        SensorType.PV_PCS_STATUS,
        SensorType.PV_PCS_MODULE_STATUS,
        SensorType.TRACKER_ZONE_STATUS,
        SensorType.TRACKER_ROW_STATUS,
        SensorType.BESS_PCS_MODULE_STATUS,
        SensorType.BESS_PCS_MODULE_ALARM,
        SensorType.BESS_PCS_STATUS,
        SensorType.BESS_BANK_STATUS,
        SensorType.BESS_STRING_STATUS,
    ]
    if device_ids is not None:
        device_ids = list(set(device_ids))
        tags_model_list = core.crud.project.tags.get_project_tags(
            project_db,
            device_ids=device_ids,
            sensor_type_ids=status_sensor_type_ids,
            deep=True,
        )
    elif tag_ids is not None:
        tags_model_list = core.crud.project.tags.get_project_tags(
            project_db,
            tag_ids=tag_ids,
            sensor_type_ids=status_sensor_type_ids,
            deep=True,
        )
    else:
        tags_model_list = core.crud.project.tags.get_project_tags(
            project_db,
            sensor_type_ids=status_sensor_type_ids,
            deep=True,
        )
    tags = tags_model_list.pandas_dataframe(index="tag_id")
    if tags.empty:
        raise HTTPException(
            status_code=404, detail="No tags found for the given request."
        )

    tags = tags[~pd.isna(tags["status_lookup_id"])]

    data = core.crud.project.data_timeseries.get_project_data_timeseries(
        project_db=project_db,
        project_name_short=project.name_short,
        tag_ids=tags.index.tolist(),
        start=pd.Timestamp(start),
        end=pd.Timestamp(end),
        interval="5min",
    )
    data_to_df = data.pandas_dataframe(
        index="time", as_datetime=True, tz=project.time_zone
    )
    if data_to_df.empty:
        return []
    ## If necessary, convert hex strings to integers.
    str_interpret = data_to_df[~pd.isna(data_to_df["value_text"])]
    if not str_interpret.empty:
        data_to_df.loc[str_interpret.index, "value_integer"] = str_interpret.loc[
            str_interpret.index, "value_text"
        ].apply(lambda x: int(x, 16))
        data_to_df.loc[str_interpret.index, "value_text"] = None
    df_timeseries = core.utils.pivot.pivot_timeseries_by_tag(
        df=data_to_df, tags=tags_model_list
    )
    df_timeseries = df_timeseries.ffill()

    # Create full time range index for alignment
    time_index = pd.date_range(
        pd.Timestamp(start).tz_convert(project.time_zone),
        pd.Timestamp(end).tz_convert(project.time_zone),
        freq="5min",
    )

    # Reindex df_timeseries to full time range and forward-fill for MQTT
    df_timeseries = df_timeseries.reindex(time_index).ffill()

    keys, vals = [], []
    for col in df_timeseries.columns:
        v = df_timeseries[col].dropna().unique()
        keys.extend([col] * len(v))
        try:
            vals.extend(v.astype(int).tolist())
        except ValueError:
            v = np.array([int(val, 16) for val in v])
            vals.extend(v.astype(int).tolist())

    try:
        status_interpret = core.crud.project.statuses.get_status_interpret(
            db=db,
            status_tags=[int(k) for k in keys],
            status_values=vals,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    lookup = {
        (d["tag"], int(d["value"]) if isinstance(d["value"], float) else d["value"]): d[
            "status"
        ]
        for d in status_interpret
    }

    def map_status(col):  # skip-star-syntax
        tag = col.name
        return col.map(
            lambda x: lookup.get((tag, x), np.nan) if pd.notnull(x) else np.nan
        )

    # Create status_strings_df from reindexed df_timeseries
    status_strings_df = df_timeseries.apply(map_status)

    status_lookup = core.crud.project.statuses.get_status_lookup(
        db=db,
        status_lookup_ids=tags["status_lookup_id"].values.tolist(),
    )

    # Create alert_df from same reindexed df_timeseries for alignment
    alert_df = pd.DataFrame()
    for col in df_timeseries.columns:
        alert_replace = {
            s["value"]: s.get("alert", False)
            for s in status_interpret
            if s["tag"] == col
        }
        alert_series = df_timeseries[col].replace(alert_replace).fillna(False)
        alert_df[col] = alert_series

    data_out = [
        {
            "x": status_strings_df.index.tz_convert(project.time_zone).tolist(),  # good
            "y": status_strings_df[col].replace(np.nan, None).tolist(),  # good
            "name": next(
                (
                    s.name_long + " " + tag.device.name_long
                    for tag in tags_model_list
                    if tag.tag_id == col
                    for s in status_lookup
                    if s.status_lookup_id == tag.status_lookup_id
                ),
                str(col),
            ),
            "alert": alert_df[col].tolist(),
            "tag_id": col,
        }
        for col in status_strings_df.columns
    ]

    return data_out


# -- time-series endpoint for Python --
@router.get("/time-series-python")
async def get_status_time_series_python(
    db: Annotated[AsyncSession, Depends(core.dependencies.get_db_async)],
    *,
    project: Annotated[models.Project, Depends(get_project_api)],
    project_db: Annotated[Session, Depends(get_project_db)],
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: list[int] | None = Query(None),
    tag_ids: list[int] | None = Query(None),
):
    try:
        data = await core.crud.project.statuses.get_status_timeseries_python(
            db=db,
            project=project,
            project_db=project_db,
            start=start,
            end=end,
            device_ids=device_ids,
            tag_ids=tag_ids,
        )
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
