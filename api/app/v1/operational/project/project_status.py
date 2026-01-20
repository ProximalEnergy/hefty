import datetime
import string
from typing import Annotated, Any, Literal

import numpy as np
import pandas as pd
from core.db_query import OutputType
from core.enumerations import SensorType
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
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
def interpret(
    db: Annotated[Session, Depends(get_project_db)],
    *,
    status_tags: Annotated[list[int], Query()] = [],
    status_values: Annotated[list[Any], Query()] = [],
):
    """todo

    Args:
        db: TODO: describe.
        status_tags: TODO: describe.
        status_values: TODO: describe.
    """
    try:
        return core.crud.project.statuses.get_status_interpret(
            db=db,
            status_tags=status_tags,
            status_values=status_values,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -- optimized /time-series endpoint for JS --
@router.get("/time-series", response_model=list[StatusTimeSeries])
async def get_status_time_series(
    db: Annotated[Session, Depends(get_project_db)],
    *,
    project: Annotated[models.Project, Depends(get_project_api)],
    project_db: Annotated[Session, Depends(get_project_db)],
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: list[int] | None = Query(None),
    tag_ids: list[int] | None = Query(None),
    device_type_ids: list[int] | None = Query(None),
    sensor_types: list[SensorType] | None = None,
):
    """sensor_types: list[SensorType] | None = None
        Only queries statuses for the provided sensor types.
        However, the provided list must be a subset of the supported sensor types.
        If not provided, all supported sensor types will be used.

    Args:
        db: TODO: describe.
        project: TODO: describe.
        project_db: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        device_ids: TODO: describe.
        tag_ids: TODO: describe.
        device_type_ids: TODO: describe.
        sensor_types: TODO: describe.
    """
    supported_sensor_types = [
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

    if sensor_types is not None:
        if not set(sensor_types).issubset(supported_sensor_types):
            unsupported_sensor_types = set(sensor_types) - set(supported_sensor_types)
            raise ValueError(f"Unsupported sensor types: {unsupported_sensor_types}")
    else:
        sensor_types = supported_sensor_types

    status_sensor_type_ids = SensorType.extract_values(enum_list=sensor_types)

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
    elif device_type_ids is not None:
        device_type_ids = list(set(device_type_ids))
        tags_model_list = core.crud.project.tags.get_project_tags(
            project_db,
            device_type_ids=device_type_ids,
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

    # Create lookup dictionary, ensuring status values are scalar strings
    lookup = {}
    for d in status_interpret:
        key = (
            d["tag"],
            int(d["value"]) if isinstance(d["value"], float) else d["value"],
        )
        status = d["status"]
        # If status is a Series (can happen with duplicate indices), extract scalar
        if isinstance(status, pd.Series):
            status = status.iloc[0] if len(status) > 0 else None
        lookup[key] = status

    # Get status_lookup before processing to determine types
    status_lookup = await core.crud.project.statuses.get_status_lookup(
        status_lookup_ids=tags["status_lookup_id"].values.tolist(),
    ).get_async(output_type=OutputType.PANDAS)

    # Create mapping from tag_id to status_lookup_id
    tag_to_status_lookup_id = tags["status_lookup_id"].to_dict()

    # Create mapping from status_lookup_id to is_string_lookup
    status_lookup_id_to_is_string = status_lookup.set_index("status_lookup_id")[
        "status_string_id"
    ].to_dict()

    # Convert string lookup columns: float -> Int64Dtype -> string
    # Note: string values must be normalized (translate + lower) to match lookup keys
    df_timeseries_typed = df_timeseries.copy()
    for col in df_timeseries_typed.columns:
        tag_id = int(col)
        status_lookup_id = tag_to_status_lookup_id.get(tag_id)
        if status_lookup_id and status_lookup_id_to_is_string.get(status_lookup_id):
            # This is a string lookup, ensure data is string and normalized
            col_series = df_timeseries_typed[col]
            if pd.api.types.is_float_dtype(col_series):
                col_series = col_series.astype("Int64").astype("string")
            elif (
                pd.api.types.is_integer_dtype(col_series)
                or pd.api.types.is_bool_dtype(col_series)
                or pd.api.types.is_string_dtype(col_series)
                or col_series.dtype == "object"
            ):
                col_series = col_series.astype("string")
            col_series = col_series.str.translate(tbl).str.lower()
            df_timeseries_typed[col] = col_series

    def map_status(col):  # nosemgrep: python-enforce-keyword-only-args
        """todo

        Args:
            col: TODO: describe.
        """
        tag = col.name

        def get_status_value(*, x):
            """Get status value, ensuring it's a scalar string."""
            if pd.isnull(x):
                return np.nan
            status = lookup.get((tag, x), np.nan)
            # If status is a Series, extract the first value
            if isinstance(status, pd.Series):
                return status.iloc[0] if len(status) > 0 else np.nan
            return status

        return col.map(lambda val: get_status_value(x=val))

    # Create status_strings_df from typed df_timeseries
    status_strings_df = df_timeseries_typed.apply(map_status)

    # Create alert_df from same reindexed df_timeseries for alignment
    alert_df = pd.DataFrame()
    for col in df_timeseries.columns:
        alert_replace = {
            s["value"]: s.get("alert", False)
            for s in status_interpret
            if s["tag"] == col
        }
        alert_series = df_timeseries[col].replace(alert_replace).fillna(False)
        # Convert any remaining non-boolean values (floats/ints) to False
        # Values not in alert_replace remain as numeric, so convert them
        mask = alert_series.apply(lambda x: isinstance(x, bool))
        alert_series[~mask] = False
        alert_df[col] = alert_series

    # 1) Extract device names from the old SQLAlchemy tag models
    #    (This is the missing "devices_df" information you need.)
    tag_device_df = pd.DataFrame(
        [
            {
                "tag_id": int(tag.tag_id),
                "device_name_long": getattr(
                    getattr(tag, "device", None), "name_long", None
                ),
                "status_lookup_id_model": getattr(tag, "status_lookup_id", None),
            }
            for tag in tags_model_list
            if getattr(tag, "tag_id", None) is not None
        ]
    ).drop_duplicates(subset=["tag_id"], keep="first")

    # 2) Enrich tags dataframe with device name
    tags_enriched = tags.copy()

    # If tag_id is an index in tags, normalize it to a column first
    if "tag_id" not in tags_enriched.columns:
        if tags_enriched.index.name == "tag_id":
            tags_enriched = tags_enriched.reset_index()
        else:
            raise KeyError(
                "tags dataframe must have tag_id column or index named 'tag_id'"
            )

    tags_enriched["tag_id"] = tags_enriched["tag_id"].astype(int, errors="ignore")

    tags_enriched = tags_enriched.merge(
        tag_device_df,
        on="tag_id",
        how="left",
        validate="many_to_one",
    )

    # Optional: if tags df is missing status_lookup_id for some rows, fill from model
    if "status_lookup_id" in tags_enriched.columns:
        tags_enriched["status_lookup_id"] = tags_enriched["status_lookup_id"].where(
            tags_enriched["status_lookup_id"].notna(),
            tags_enriched["status_lookup_id_model"],
        )
    else:
        # if tags df doesn't have it at all, use the model-derived one
        tags_enriched["status_lookup_id"] = tags_enriched["status_lookup_id_model"]

    # 3) Build a status_lookup_id -> status_name_long dict from status_lookup dataframe
    status_lookup_df = (
        status_lookup  # rename for clarity if your variable is named differently
    )
    status_name_by_id = (
        status_lookup_df.dropna(subset=["status_lookup_id"])
        .set_index("status_lookup_id")["name_long"]
        .astype(str)
        .to_dict()
    )

    # 4) Build tag_id -> (status_lookup_id, device_name_long) lookup
    tag_row_by_id = tags_enriched.drop_duplicates(
        subset=["tag_id"], keep="first"
    ).set_index("tag_id")[["status_lookup_id", "device_name_long"]]

    def make_series_name(tag_id) -> str:  # nosemgrep: python-enforce-keyword-only-args
        try:
            row = tag_row_by_id.loc[int(tag_id)]
        except Exception:
            return str(tag_id)

        status_id = row.get("status_lookup_id", None)
        device_name = row.get("device_name_long", None)
        status_name = status_name_by_id.get(status_id, None)

        parts = []
        if status_name and status_name != "nan":
            parts.append(str(status_name))
        if device_name and device_name != "nan":
            parts.append(str(device_name))

        return " ".join(parts) if parts else str(tag_id)

    # 5) Use it in your output
    data_out = [
        {
            "x": status_strings_df.index.tz_convert(project.time_zone).tolist(),
            "y": status_strings_df[col].replace(np.nan, None).tolist(),
            "name": make_series_name(col),
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
    device_type_ids: list[int] | None = Query(None),
    sensor_types: list[SensorType] | None = None,
):
    """todo

    Args:
        db: TODO: describe.
        project: TODO: describe.
        project_db: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        device_ids: TODO: describe.
        tag_ids: TODO: describe.
        device_type_ids: TODO: describe.
        sensor_types: TODO: describe.
    """
    try:
        data = await core.crud.project.statuses.get_status_timeseries_python(
            db=db,
            project=project,
            project_db=project_db,
            start=start,
            end=end,
            device_ids=device_ids,
            tag_ids=tag_ids,
            device_type_ids=device_type_ids,
            sensor_types=sensor_types,
        )
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/last-known-statuses", response_model=list[DeviceStatus])
async def get_last_known_statuses(
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
