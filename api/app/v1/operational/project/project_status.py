import datetime
import json
import string
from typing import Annotated, Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
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


# -- utility function unchanged --
def validate_status_tags_and_values(
    *,
    status_tags: list[int],
    status_values: list[Any],
):  # skip-star-syntax
    if len(status_tags) != len(status_values) or len(status_tags) == 0:
        raise ValueError(
            "Status tags and values must be the same length and greater than 0",
        )


# -- vectorized status interpret --
def get_status_interpret(
    *,
    db: Annotated[Session, Depends(get_project_db)],
    status_tags: Annotated[list[int], Query()] = [],
    status_values: Annotated[list[Any], Query()] = [],
):
    validate_status_tags_and_values(
        status_tags=status_tags,
        status_values=status_values,
    )

    status_types = ["status_binary_id", "status_boolean_id", "status_string_id"]
    tags = core.crud.project.tags.get_project_tags(db, tag_ids=status_tags).models()
    status_lookup_ids = {
        tag.tag_id: tag.status_lookup_id
        for tag in tags
        if tag.status_lookup_id is not None
    }
    if len(status_lookup_ids) == 0:
        raise HTTPException(
            status_code=404, detail="Status tags not configured for device."
        )
    status_lookup_df = core.crud.project.statuses.get_status_lookup(
        db=db,
        status_lookup_ids=[
            sid for sid in status_lookup_ids.values() if sid is not None
        ],
    ).pandas_dataframe()
    if status_lookup_df.empty:
        raise HTTPException(
            status_code=404, detail="Status tables not found for project."
        )

    df = pd.DataFrame({"tag": status_tags, "value": status_values})
    df["status_lookup_id"] = df["tag"].map(status_lookup_ids)
    df = df.merge(
        status_lookup_df[["status_lookup_id", *status_types]],
        on="status_lookup_id",
        how="left",
    )

    result_list = []

    for status_type in status_types:
        status_df = df[df[status_type].notna()].copy()
        if status_df.empty:
            continue

        if status_type == "status_binary_id":
            status_df["value"] = status_df["value"].astype(int)
            status_binary_df = core.crud.project.statuses.get_status_binary(
                db=db,
                status_binary_ids=status_df[status_type].tolist(),
            ).pandas_dataframe()
            grouped = status_binary_df.groupby("status_binary_id")

            def decode_binary(row, grouped):  # skip-star-syntax
                try:
                    sub_df = grouped.get_group(row["status_binary_id"]).set_index(
                        "bit_position"
                    )
                except KeyError:
                    return pd.Series([None, None, False])
                binary_value = bin(int(row.value))[2:][::-1].ljust(sub_df.shape[0], "0")  # noqa: FURB116
                status_out, alert = {}, False
                for i, bit_val in enumerate(binary_value):
                    status_column = "state_true" if bit_val == "1" else "state_false"
                    if status_column == "state_false":
                        continue
                    nominal_state = sub_df.loc[i, "nominal_state"]
                    desc = sub_df.loc[i, "description"]
                    status = sub_df.loc[i, status_column]
                    if status is not None:
                        status_out[desc] = status
                        if (nominal_state is not None) and (
                            bool(int(bit_val)) is not nominal_state
                        ):
                            alert = True
                        elif nominal_state is None:
                            pass
                failure_mode = sub_df.loc[i, "failure_mode_id"] if alert else None
                return pd.Series([json.dumps(status_out), failure_mode, alert])

            status_df[["status", "failure_mode_id", "alert"]] = status_df.apply(
                lambda row: decode_binary(row, grouped), axis=1
            )
            result_list.append(
                status_df[["tag", "value", "status", "failure_mode_id", "alert"]]
            )

        elif status_type == "status_boolean_id":
            status_df["value"] = status_df["value"].map(
                lambda x: bool(strtobool(str(int(float(x)))))
            )
            status_boolean = core.crud.project.statuses.get_status_boolean(
                db=db,
                status_boolean_ids=status_df[status_type].tolist(),
            ).models()
            status_boolean_df = pd.DataFrame([obj.__dict__ for obj in status_boolean])
            status_boolean_df = status_boolean_df.drop(
                columns="_sa_instance_state", errors="ignore"
            )
            status_boolean_df = status_boolean_df.set_index(status_type)

            def resolve_bool(row):  # skip-star-syntax
                entry = status_boolean_df.loc[row[status_type]]
                if entry is None:
                    return pd.Series(["Unknown", None])
                status = entry["state_true"] if row["value"] else entry["state_false"]
                failure_mode = entry["failure_mode_id"] if status is not None else None
                return pd.Series([status, failure_mode])

            status_df[["status", "failure_mode_id"]] = status_df.apply(
                resolve_bool, axis=1
            )
            result_list.append(status_df[["tag", "value", "status", "failure_mode_id"]])

        elif status_type == "status_string_id":
            status_df["value"] = (
                status_df["value"].astype(str).str.translate(tbl).str.lower()  # type: ignore
            )
            status_string = core.crud.project.statuses.get_status_string(
                db=db,
                status_string_ids=status_df[status_type].tolist(),
            ).models()
            status_string_df = pd.DataFrame([obj.__dict__ for obj in status_string])
            status_string_df = status_string_df.drop(
                columns="_sa_instance_state", errors="ignore"
            )
            status_string_df = status_string_df.set_index("string_trigger")

            def resolve_string(row):  # skip-star-syntax
                try:
                    entry = status_string_df.loc[row.value]
                    return pd.Series([entry["description"], entry["failure_mode_id"]])
                except KeyError:
                    return pd.Series(["Unknown", None])

            status_df[["status", "failure_mode_id"]] = status_df.apply(
                resolve_string, axis=1
            )
            result_list.append(status_df[["tag", "value", "status", "failure_mode_id"]])

    df_out = pd.concat(result_list, ignore_index=True)
    return df_out.replace({np.nan: None}).to_dict(orient="records")


# -- unchanged interpret wrapper --
@router.get("/interpret")
def interpret(
    db: Annotated[Session, Depends(get_project_db)],
    *,
    status_tags: Annotated[list[int], Query()] = [],
    status_values: Annotated[list[Any], Query()] = [],
):
    return get_status_interpret(
        db=db,
        status_tags=status_tags,
        status_values=status_values,
    )


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
    status_sensor_type_ids = [46, 47, 48, 49, 137, 140, 142, 143, 145]
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

    status_interpret = get_status_interpret(
        db=db,
        status_tags=[int(k) for k in keys],
        status_values=vals,
    )

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
def get_status_time_series_python(
    db: Annotated[Session, Depends(get_project_db)],
    *,
    project: Annotated[models.Project, Depends(get_project_api)],
    project_db: Annotated[Session, Depends(get_project_db)],
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: list[int] | None = Query(None),
    tag_ids: list[int] | None = Query(None),
):
    status_sensor_type_ids = [46, 47, 48, 49, 137, 140, 142, 143, 145]
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

    status_interpret = get_status_interpret(
        db=db,
        status_tags=[int(k) for k in keys],
        status_values=vals,
    )

    lookup = {
        (d["tag"], int(d["value"]) if isinstance(d["value"], float) else d["value"]): d[
            "failure_mode_id"
        ]
        for d in status_interpret
    }

    def map_status(col):  # skip-star-syntax
        tag = col.name
        return col.map(
            lambda x: lookup.get((tag, x), np.nan) if pd.notnull(x) else np.nan
        )

    status_failure_mode_df = df_timeseries.apply(map_status).astype("Int64")
    status_failure_mode_df = status_failure_mode_df.reset_index(drop=False)
    status_failure_mode_df = status_failure_mode_df.astype(object).where(
        pd.notnull(status_failure_mode_df), None
    )

    return status_failure_mode_df.to_dict(orient="records")
