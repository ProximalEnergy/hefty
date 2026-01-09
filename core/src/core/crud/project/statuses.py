import datetime
import json
import string
from typing import Any, Literal

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from core import models
from core.db_query import DbQuery, OutputType
from core.enumerations import SensorType, TimeInterval, TimeOffset
from core.model_list import ModelList

# Cache translation table outside the endpoint
delete_chars = string.punctuation + string.whitespace
tbl = str.maketrans("", "", delete_chars)


def strtobool(val: str) -> int:  # nosemgrep: python-enforce-keyword-only-args
    """TODO: add description.

    Args:
        val: TODO: describe.
    """
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
):  # nosemgrep: python-enforce-keyword-only-args
    """TODO: add description.

    Args:
        status_tags: TODO: describe.
        status_values: TODO: describe.
    """
    if len(status_tags) != len(status_values) or len(status_tags) == 0:
        raise ValueError(
            "Status tags and values must be the same length and greater than 0",
        )


# -- vectorized status interpret --
async def get_status_interpret_async(
    db: AsyncSession,
    *,
    project_db: AsyncSession | Session,
    status_tags: list[int] = [],
    status_values: list[Any] = [],
):
    """TODO: add description.

    Args:
        db: TODO: describe.
        project_db: TODO: describe.
        status_tags: TODO: describe.
        status_values: TODO: describe.
    """
    validate_status_tags_and_values(
        status_tags=status_tags,
        status_values=status_values,
    )

    status_types = ["status_binary_id", "status_boolean_id", "status_string_id"]
    # Get tags from project schema - handle both sync and async sessions
    if isinstance(project_db, AsyncSession):
        stmt = select(models.Tag).where(models.Tag.tag_id.in_(status_tags))
        result = await project_db.execute(stmt)
        tags = list(result.scalars().all())
    else:
        # Sync session - use sync query
        tags = core.crud.project.tags.get_project_tags(
            project_db, tag_ids=status_tags
        ).models()
    status_lookup_ids = {
        tag.tag_id: tag.status_lookup_id
        for tag in tags
        if tag.status_lookup_id is not None
    }
    if len(status_lookup_ids) == 0:
        raise ValueError("Status tags not configured for device.")
    status_lookup_list = await core.crud.project.statuses.get_status_lookup_async(
        db=db,
        status_lookup_ids=[
            sid for sid in status_lookup_ids.values() if sid is not None
        ],
    )
    if len(status_lookup_list) == 0:
        raise ValueError("Status tables not found for project.")
    # Convert to pandas dataframe
    status_lookup_df = pd.DataFrame([obj.__dict__ for obj in status_lookup_list])
    status_lookup_df = status_lookup_df.drop(
        columns="_sa_instance_state", errors="ignore"
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
            status_binary_list = (
                await core.crud.project.statuses.get_status_binary_async(
                    db=db,
                    status_binary_ids=status_df[status_type].tolist(),
                )
            )
            status_binary_df = pd.DataFrame(
                [obj.__dict__ for obj in status_binary_list]
            )
            status_binary_df = status_binary_df.drop(
                columns="_sa_instance_state", errors="ignore"
            )
            grouped = status_binary_df.groupby("status_binary_id")

            def decode_binary(
                *,
                row,
                grouped,
            ):  # nosemgrep: python-enforce-keyword-only-args
                """TODO: add description.

                Args:
                    row: TODO: describe.
                    grouped: TODO: describe.
                """
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
                lambda row: decode_binary(row=row, grouped=grouped),
                axis=1,
            )
            result_list.append(
                status_df[["tag", "value", "status", "failure_mode_id", "alert"]]
            )

        elif status_type == "status_boolean_id":
            status_df["value"] = status_df["value"].map(
                lambda x: bool(strtobool(str(int(float(x)))))
            )
            status_boolean_list = (
                await core.crud.project.statuses.get_status_boolean_async(
                    db=db,
                    status_boolean_ids=status_df[status_type].tolist(),
                )
            )
            status_boolean_df = pd.DataFrame(
                [obj.__dict__ for obj in status_boolean_list]
            )
            status_boolean_df = status_boolean_df.drop(
                columns="_sa_instance_state", errors="ignore"
            )
            status_boolean_df = status_boolean_df.set_index(status_type)

            def resolve_bool(
                *,
                row,
            ):  # nosemgrep: python-enforce-keyword-only-args
                """TODO: add description.

                Args:
                    row: TODO: describe.
                """
                entry = status_boolean_df.loc[row[status_type]]
                if entry is None:
                    return pd.Series(["Unknown", None])
                status = entry["state_true"] if row["value"] else entry["state_false"]
                failure_mode = entry["failure_mode_id"] if status is not None else None
                return pd.Series([status, failure_mode])

            status_df[["status", "failure_mode_id"]] = status_df.apply(
                lambda row: resolve_bool(row=row),
                axis=1,
            )
            result_list.append(status_df[["tag", "value", "status", "failure_mode_id"]])

        elif status_type == "status_string_id":
            status_df["value"] = (
                status_df["value"].astype(str).str.translate(tbl).str.lower()  # type: ignore
            )
            status_string_list = (
                await core.crud.project.statuses.get_status_string_async(
                    db=db,
                    status_string_ids=status_df[status_type].tolist(),
                )
            )
            status_string_df = pd.DataFrame(
                [obj.__dict__ for obj in status_string_list]
            )
            status_string_df = status_string_df.drop(
                columns="_sa_instance_state", errors="ignore"
            )
            status_string_df = status_string_df.set_index("string_trigger")

            def resolve_string(
                *,
                row,
            ):  # nosemgrep: python-enforce-keyword-only-args
                """TODO: add description.

                Args:
                    row: TODO: describe.
                """
                try:
                    entry = status_string_df.loc[row.value]
                    return pd.Series([entry["description"], entry["failure_mode_id"]])
                except KeyError:
                    return pd.Series(["Unknown", None])

            status_df[["status", "failure_mode_id"]] = status_df.apply(
                lambda row: resolve_string(row=row),
                axis=1,
            )
            result_list.append(status_df[["tag", "value", "status", "failure_mode_id"]])

    df_out = pd.concat(result_list, ignore_index=True)
    return df_out.replace({np.nan: None}).to_dict(orient="records")


# -- vectorized status interpret --
def get_status_interpret(
    db: Session,
    *,
    status_tags: list[int] = [],
    status_values: list[Any] = [],
):
    """TODO: add description.

    Args:
        db: TODO: describe.
        status_tags: TODO: describe.
        status_values: TODO: describe.
    """
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
        raise ValueError("Status tags not configured for device.")
    status_lookup_df = core.crud.project.statuses.get_status_lookup(
        db=db,
        status_lookup_ids=[
            sid for sid in status_lookup_ids.values() if sid is not None
        ],
    ).pandas_dataframe()
    if status_lookup_df.empty:
        raise ValueError("Status tables not found for project.")

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

            def decode_binary(
                *,
                row,
                grouped,
            ):  # nosemgrep: python-enforce-keyword-only-args
                """TODO: add description.

                Args:
                    row: TODO: describe.
                    grouped: TODO: describe.
                """
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
                lambda row: decode_binary(row=row, grouped=grouped),
                axis=1,
            )
            result_list.append(
                status_df[["tag", "value", "status", "failure_mode_id", "alert"]]
            )

        elif status_type == "status_boolean_id":
            status_df["value"] = status_df["value"].map(
                lambda x: bool(strtobool(str(int(float(x)))))
            )
            status_boolean = core.crud.project.statuses.get_status_boolean(
                status_boolean_ids=status_df[status_type].tolist(),
            ).get(output_type=OutputType.SQLALCHEMY)
            status_boolean_df = pd.DataFrame([obj.__dict__ for obj in status_boolean])
            status_boolean_df = status_boolean_df.drop(
                columns="_sa_instance_state", errors="ignore"
            )
            status_boolean_df = status_boolean_df.set_index(status_type)

            def resolve_bool(row):  # nosemgrep: python-enforce-keyword-only-args
                """TODO: add description.

                Args:
                    row: TODO: describe.
                """
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
                status_string_ids=status_df[status_type].tolist(),
            ).get(output_type=OutputType.SQLALCHEMY)
            status_string_df = pd.DataFrame([obj.__dict__ for obj in status_string])
            status_string_df = status_string_df.drop(
                columns="_sa_instance_state", errors="ignore"
            )
            status_string_df = status_string_df.set_index("string_trigger")

            def resolve_string(row):  # nosemgrep: python-enforce-keyword-only-args
                """TODO: add description.

                Args:
                    row: TODO: describe.
                """
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


def get_status_lookup(
    db: Session,
    *,
    status_lookup_ids: list[int] = [],
    return_query: bool = False,
) -> ModelList[models.StatusLookup]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        status_lookup_ids: TODO: describe.
        return_query: TODO: describe.
    """
    query = db.query(models.StatusLookup)
    if status_lookup_ids:
        query = query.where(
            models.StatusLookup.status_lookup_id.in_(status_lookup_ids),
        )
    return ModelList(query=query, return_query=return_query)


def get_status_binary(
    db: Session,
    *,
    status_binary_ids: list[int] = [],
    return_query: bool = False,
) -> ModelList[models.StatusBinary]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        status_binary_ids: TODO: describe.
        return_query: TODO: describe.
    """
    query = db.query(models.StatusBinary)
    if status_binary_ids:
        query = query.where(
            models.StatusBinary.status_binary_id.in_(status_binary_ids),
        )
    return ModelList(query=query, return_query=return_query)


def get_status_boolean(
    *,
    status_boolean_ids: list[int] = [],
) -> DbQuery[models.StatusBoolean, Literal[False]]:
    """TODO: add description.

    Args:
        status_boolean_ids: TODO: describe.
    """
    stmt = select(models.StatusBoolean)
    if status_boolean_ids:
        stmt = stmt.where(
            models.StatusBoolean.status_boolean_id.in_(status_boolean_ids),
        )
    return DbQuery(query=stmt)


def get_status_string(
    *,
    status_string_ids: list[int] = [],
) -> DbQuery[models.StatusString, Literal[False]]:
    """TODO: add description.

    Args:
        status_string_ids: TODO: describe.
    """
    stmt = select(models.StatusString)
    if status_string_ids:
        stmt = stmt.where(
            models.StatusString.status_string_id.in_(status_string_ids),
        )
    return DbQuery(query=stmt)


# --- ASYNC SECTION ---
async def get_status_lookup_async(
    db: AsyncSession,
    *,
    status_lookup_ids: list[int] = [],
) -> list[models.StatusLookup]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        status_lookup_ids: TODO: describe.
    """
    stmt = select(models.StatusLookup)
    if status_lookup_ids:
        stmt = stmt.where(
            models.StatusLookup.status_lookup_id.in_(status_lookup_ids),
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_status_binary_async(
    db: AsyncSession,
    *,
    status_binary_ids: list[int] = [],
) -> list[models.StatusBinary]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        status_binary_ids: TODO: describe.
    """
    stmt = select(models.StatusBinary)
    if status_binary_ids:
        stmt = stmt.where(
            models.StatusBinary.status_binary_id.in_(status_binary_ids),
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_status_boolean_async(
    db: AsyncSession,
    *,
    status_boolean_ids: list[int] = [],
) -> list[models.StatusBoolean]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        status_boolean_ids: TODO: describe.
    """
    stmt = select(models.StatusBoolean)
    if status_boolean_ids:
        stmt = stmt.where(
            models.StatusBoolean.status_boolean_id.in_(status_boolean_ids),
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_status_string_async(
    db: AsyncSession,
    *,
    status_string_ids: list[int] = [],
) -> list[models.StatusString]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        status_string_ids: TODO: describe.
    """
    stmt = select(models.StatusString)
    if status_string_ids:
        stmt = stmt.where(
            models.StatusString.status_string_id.in_(status_string_ids),
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_status_timeseries_python(
    db: AsyncSession,
    *,
    project: models.Project,
    project_db: Session,
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: list[int] | None = None,
    tag_ids: list[int] | None = None,
    device_type_ids: list[int] | None = None,
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
    tags = tags[~pd.isna(tags["status_lookup_id"])]

    # Early return if no tags with status_lookup_id
    if tags.empty:
        # Create empty DataFrame with time column matching successful format
        try:
            time_index = pd.date_range(
                pd.Timestamp(start).tz_convert(project.time_zone),
                pd.Timestamp(end).tz_convert(project.time_zone),
                freq="5min",
            )
        except Exception:
            time_index = pd.date_range(
                pd.Timestamp(start).tz_localize(project.time_zone),
                pd.Timestamp(end).tz_localize(project.time_zone),
                freq="5min",
            )
        empty_df = pd.DataFrame({"time": time_index})
        return empty_df.to_dict(orient="records")

    data = await core.crud.project.data_timeseries.DataTimeseries.get(
        project_name_short=project.name_short,
        tag_ids=tags.index.tolist(),
        query_start=pd.Timestamp(start),
        query_end=pd.Timestamp(end),
        agg_interval=TimeInterval.FIVE_MINUTES,
        max_lookback_period=TimeOffset.NONE,
        ensure_full_range=True,
        project_db=project_db,
        operational_db=db,
        return_arrow=False,
    )
    data_to_df = data.df.to_pandas()

    if data_to_df.empty:
        # Create empty DataFrame with time column matching successful format
        time_index = pd.date_range(
            pd.Timestamp(start).tz_convert(project.time_zone),
            pd.Timestamp(end).tz_convert(project.time_zone),
            freq="5min",
        )
        empty_df = pd.DataFrame({"time": time_index})
        return empty_df.to_dict(orient="records")

    data_to_df = data_to_df.set_index("time", drop=True)
    data_to_df.columns = data_to_df.columns.astype(int)
    # Forward fill, normalize hex string values, then convert to nullable Int32
    data_to_df = data_to_df.ffill()

    def _maybe_hex(value):  # nosemgrep: python-enforce-keyword-only-args
        """TODO: add description.

        Args:
            value: TODO: describe.
        """
        if isinstance(value, str):
            trimmed = value.strip().lower()
            if trimmed.startswith("0x"):
                try:
                    return int(trimmed, 16)
                except ValueError:
                    return value
        return value

    for column in data_to_df.columns:
        data_to_df[column] = data_to_df[column].map(_maybe_hex)
    data_to_df = data_to_df.astype("Int32")
    df_timeseries = data_to_df.copy()

    # Create full time range index for alignment
    start = pd.Timestamp(start)
    if start.tzinfo is None:
        start = start.tz_localize(project.time_zone)
    else:
        start = start.tz_convert(project.time_zone)
    end = pd.Timestamp(end)
    if end.tzinfo is None:
        end = end.tz_localize(project.time_zone)
    else:
        end = end.tz_convert(project.time_zone)
    time_index = pd.date_range(
        start,
        end,
        freq="5min",
    )

    # Reindex df_timeseries to full time range and forward-fill for MQTT
    df_timeseries = df_timeseries.reindex(time_index).ffill()

    # Handle empty df_timeseries or no columns
    if df_timeseries.empty or len(df_timeseries.columns) == 0:
        empty_df = pd.DataFrame({"time": time_index})
        return empty_df.to_dict(orient="records")

    keys, vals = [], []
    for col in df_timeseries.columns:
        v = df_timeseries[col].dropna().unique()
        keys.extend([col] * len(v))
        try:
            vals.extend(v.astype(int).tolist())
        except ValueError:
            v = np.array([int(val, 16) for val in v])
            vals.extend(v.astype(int).tolist())

    # Handle case where no keys/vals found
    if not keys or not vals:
        empty_df = pd.DataFrame({"time": time_index})
        return empty_df.to_dict(orient="records")

    status_interpret = await get_status_interpret_async(
        db=db,
        project_db=project_db,
        status_tags=[int(k) for k in keys],
        status_values=vals,
    )

    lookup = {
        (d["tag"], int(d["value"]) if isinstance(d["value"], float) else d["value"]): d[
            "failure_mode_id"
        ]
        for d in status_interpret
    }

    def map_status(col):  # nosemgrep: python-enforce-keyword-only-args
        """TODO: add description.

        Args:
            col: TODO: describe.
        """
        tag = col.name
        return col.map(
            lambda x: lookup.get((tag, x), np.nan) if pd.notnull(x) else np.nan
        )

    status_failure_mode_df = df_timeseries.apply(map_status).astype("Int64")
    status_failure_mode_df = status_failure_mode_df.reset_index(drop=False)
    status_failure_mode_df = status_failure_mode_df.astype(object).where(
        pd.notnull(status_failure_mode_df), None
    )

    # Final check - if DataFrame is empty, return empty structure with time column
    if status_failure_mode_df.empty:
        empty_df = pd.DataFrame({"time": time_index})
        return empty_df.to_dict(orient="records")

    return status_failure_mode_df.to_dict(orient="records")
