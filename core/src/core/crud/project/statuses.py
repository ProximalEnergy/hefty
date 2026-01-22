import datetime
import json
import string
from typing import Any, Literal

import numpy as np
import pandas as pd
from pandas._libs.missing import NAType
from sqlalchemy import case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.sql.sqltypes import Text

import core
from core import models
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import DbQuery, OutputType
from core.enumerations import SensorType, TimeInterval, TimeOffset

# Cache translation table outside the endpoint
delete_chars = string.punctuation + string.whitespace
tbl = str.maketrans("", "", delete_chars)


def strtobool(val: str) -> int:  # nosemgrep: python-enforce-keyword-only-args
    """Convert a truthy/falsey string to 1 or 0.

    Args:
        val: String representation of a boolean value.
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
    """Validate that status tags and values lists are non-empty and aligned.

    Args:
        status_tags: Tag ids whose statuses are being interpreted.
        status_values: Raw status values corresponding to each tag.
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
    """Interpret status values into human-readable status data asynchronously.

    Args:
        db: Async session for operational status lookup tables.
        project_db: Project session for tag metadata.
        status_tags: Tag ids whose statuses should be interpreted.
        status_values: Raw status values for each tag.
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
                """Decode a binary status value into a status payload.

                Args:
                    row: Row containing status lookup ids and value.
                    grouped: Status binary table grouped by status_binary_id.
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
                """Resolve a boolean status into status text and failure mode.

                Args:
                    row: Row containing status lookup id and value.
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
                """Resolve a string status into status text and failure mode.

                Args:
                    row: Row containing status lookup id and value.
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
    """Interpret status values into human-readable status data.

    Args:
        db: Sync session for operational status lookup tables.
        status_tags: Tag ids whose statuses should be interpreted.
        status_values: Raw status values for each tag.
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
        status_lookup_ids=[
            sid for sid in status_lookup_ids.values() if sid is not None
        ],
    ).get(output_type=OutputType.PANDAS)
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
                status_binary_ids=status_df[status_type].tolist(),
            ).get(output_type=OutputType.PANDAS)
            grouped = status_binary_df.groupby("status_binary_id")

            def decode_binary(
                *,
                row,
                grouped,
            ):  # nosemgrep: python-enforce-keyword-only-args
                """Decode a binary status value into a status payload.

                Args:
                    row: Row containing status lookup ids and value.
                    grouped: Status binary table grouped by status_binary_id.
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
                """Resolve a boolean status into status text and failure mode.

                Args:
                    row: Row containing status lookup id and value.
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
                """Resolve a string status into status text and failure mode.

                Args:
                    row: Row containing status lookup id and value.
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
    *,
    status_lookup_ids: list[int] = [],
) -> DbQuery[models.StatusLookup, Literal[False]]:
    """Get the status_lookup table.

    Args:
        status_lookup_ids: Filter to only included status_lookup_ids.
    """
    stmt = select(models.StatusLookup)
    if status_lookup_ids:
        stmt = stmt.where(
            models.StatusLookup.status_lookup_id.in_(status_lookup_ids),
        )
    return DbQuery(query=stmt)


def get_status_binary(
    *,
    status_binary_ids: list[int] = [],
) -> DbQuery[models.StatusBinary, Literal[False]]:
    """Get the status_binary table.

    Args:
        status_binary_ids: Filter to only included status_binary_ids.
    """
    stmt = select(models.StatusBinary)
    if status_binary_ids:
        stmt = stmt.where(
            models.StatusBinary.status_binary_id.in_(status_binary_ids),
        )
    return DbQuery(query=stmt)


def get_status_boolean(
    *,
    status_boolean_ids: list[int] = [],
) -> DbQuery[models.StatusBoolean, Literal[False]]:
    """Build a query for status boolean rows.

    Args:
        status_boolean_ids: Status boolean ids to filter by.
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
    """Build a query for status string rows.

    Args:
        status_string_ids: Status string ids to filter by.
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
    """Fetch status lookup rows asynchronously by id.

    Args:
        db: Async session for operational status tables.
        status_lookup_ids: Status lookup ids to filter by.
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
    """Fetch status binary rows asynchronously by id.

    Args:
        db: Async session for operational status tables.
        status_binary_ids: Status binary ids to filter by.
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
    """Fetch status boolean rows asynchronously by id.

    Args:
        db: Async session for operational status tables.
        status_boolean_ids: Status boolean ids to filter by.
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
    """Fetch status string rows asynchronously by id.

    Args:
        db: Async session for operational status tables.
        status_string_ids: Status string ids to filter by.
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
        db: Async session for operational metadata.
        project: Project instance containing timezone information.
        project_db: Project database session for tag lookups.
        start: Query start time.
        end: Query end time.
        device_ids: Optional device ids to scope tags.
        tag_ids: Optional tag ids to scope tags.
        device_type_ids: Optional device type ids to scope tags.
        sensor_types: Optional sensor types to include.
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

    data_timeseries = DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=tags.index.tolist(),
        query_start=pd.Timestamp(start).to_pydatetime(),
        query_end=pd.Timestamp(end).to_pydatetime(),
        freq=TimeInterval.FIVE_MINUTES,
        max_lookback_period=TimeOffset.NONE,
        ensure_full_range=True,
        project_db=project_db,
    )
    data = await data_timeseries.get()
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
        """Convert hex string values to integers when possible.

        Args:
            value: Raw value from the dataframe cell.
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
        """Map status values to failure mode ids for a column.

        Args:
            col: Series of status values for a tag.
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


########################################################
# Last Known Statuses
########################################################


def get_last_known_statuses_query(
    *,
    device_type_ids: list[int] | None = None,
    sensor_type_ids: list[int] | None = None,
    tag_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
):
    """
    Do a big fat join to retrieve the following columns:
    - time (from DataTimeseriesLast)
    - tag_id (from DataTimeseriesLast)
    - device_id (from Tag)
    - status_lookup_id (from Tag)
    - value (coalesced from value_integer, value_bigint,
        value_real, value_boolean, value_text)
    - value_type (calculated from value_integer, value_bigint,
        value_real, value_boolean, value_text)
    - lookup_id (coalesced from status_binary_id, status_string_id, status_boolean_id)
    - lookup_table_name (calculated from status_binary_id,
        status_string_id, status_boolean_id)
    """

    dtl = models.DataTimeseriesLast
    t = models.Tag
    d = models.Device
    sl = models.StatusLookup

    # ---- value columns ----

    value = func.coalesce(
        cast(dtl.value_integer, Text),
        cast(dtl.value_bigint, Text),
        cast(dtl.value_real, Text),
        cast(dtl.value_boolean, Text),
        cast(dtl.value_text, Text),
    ).label("value")

    value_type = case(
        (dtl.value_integer.isnot(None), "integer"),
        (dtl.value_bigint.isnot(None), "bigint"),
        (dtl.value_real.isnot(None), "real"),
        (dtl.value_boolean.isnot(None), "boolean"),
        (dtl.value_text.isnot(None), "text"),
        else_=None,
    ).label("value_type")

    lookup_id = func.coalesce(
        sl.status_binary_id,
        sl.status_string_id,
        sl.status_boolean_id,
    ).label("lookup_id")

    lookup_table_name = case(
        (sl.status_binary_id.isnot(None), "status_binary"),
        (sl.status_string_id.isnot(None), "status_string"),
        (sl.status_boolean_id.isnot(None), "status_boolean"),
        else_=None,
    ).label("lookup_table_name")

    # ---- base statement ----

    stmt = (
        select(
            dtl.time.label("time"),
            dtl.tag_id.label("tag_id"),
            t.device_id.label("device_id"),
            t.status_lookup_id.label("status_lookup_id"),
            value,
            value_type,
            lookup_id,
            lookup_table_name,
        )
        .select_from(dtl)
        .join(dtl.tag)  # dtl -> tag
        .join(t.device)  # tag -> device
        .join(sl, sl.status_lookup_id == t.status_lookup_id)
        .where(t.status_lookup_id.isnot(None))
    )

    # ---- keep existing filters ----

    if device_type_ids:
        stmt = stmt.where(d.device_type_id.in_(device_type_ids))

    if sensor_type_ids:
        stmt = stmt.where(t.sensor_type_id.in_(sensor_type_ids))

    if tag_ids:
        stmt = stmt.where(dtl.tag_id.in_(tag_ids))

    if device_ids:
        stmt = stmt.where(t.device_id.in_(device_ids))

    return DbQuery(query=stmt)


async def get_last_known_statuses(
    *,
    project: models.Project,
    device_type_ids: list[int] | None = None,
    sensor_type_ids: list[int] | None = None,
    tag_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
    alert_only: bool = True,
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
                ]
        },
            {
            "device_id": ...,
            "statuses": [
                {"time": "...", "status": "...", "status_type": "..."},
                {"time": "...", "status": "...", "status_type": "..."},
                ...
                ]
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
    data_last_query = get_last_known_statuses_query(
        device_type_ids=device_type_ids,
        sensor_type_ids=sensor_type_ids,
        tag_ids=tag_ids,
        device_ids=device_ids,
    )
    df = await data_last_query.get_async(
        output_type=OutputType.PANDAS, schema=project.name_short
    )
    df = df[df["lookup_id"].notna() & df["value"].notna()].copy().reset_index(drop=True)
    binary_df = (
        df[df["lookup_table_name"] == "status_binary"].copy().reset_index(drop=True)
    )
    boolean_df = (
        df[df["lookup_table_name"] == "status_boolean"].copy().reset_index(drop=True)
    )
    string_df = (
        df[df["lookup_table_name"] == "status_string"].copy().reset_index(drop=True)
    )
    if not binary_df.empty:
        binary_df["value"] = pd.to_numeric(binary_df["value"], errors="coerce")

        lookup_ids = binary_df["lookup_id"].dropna().unique().tolist()
        status_binary_query = get_status_binary(status_binary_ids=lookup_ids)

        status_binary_df = await status_binary_query.get_async(
            output_type=OutputType.PANDAS
        )

        if alert_only:
            alert_mask = _detect_binary_alerts(
                binary_df=binary_df, status_binary_df=status_binary_df
            )
            binary_df = binary_df.loc[alert_mask].copy()

        # Ensure expected columns exist & bit_position is int
        status_binary_df = status_binary_df.copy()
        status_binary_df["bit_position"] = status_binary_df["bit_position"].astype(int)

        binary_df = _interpret_binary_statuses(
            binary_df=binary_df, status_binary_df=status_binary_df
        )
    if not string_df.empty:
        # Fetch lookup rows
        string_df["value"] = string_df["value"].astype("string")  # ensure consistent
        lookup_ids = string_df["lookup_id"].dropna().unique().tolist()
        status_string_query = get_status_string(status_string_ids=lookup_ids)

        status_string_df = await status_string_query.get_async(
            output_type=OutputType.PANDAS
        )

        string_df = _interpret_string_statuses(
            string_df=string_df, status_string_df=status_string_df
        )

        if alert_only:
            string_df = string_df.loc[string_df["alert"]].copy()

    if not boolean_df.empty:
        # Fetch lookup rows
        lookup_ids = boolean_df["lookup_id"].dropna().unique().tolist()
        status_boolean_query = get_status_boolean(status_boolean_ids=lookup_ids)

        status_boolean_df = await status_boolean_query.get_async(
            output_type=OutputType.PANDAS
        )

        boolean_df = _interpret_boolean_statuses(
            boolean_df=boolean_df, status_boolean_df=status_boolean_df
        )

        if alert_only:
            boolean_df = boolean_df.loc[boolean_df["alert"]].copy()
    out = pd.concat([binary_df, string_df, boolean_df], ignore_index=True)
    return _to_frontend_status_payload(df=out)


def _interpret_binary_statuses(
    *, binary_df: pd.DataFrame, status_binary_df: pd.DataFrame
) -> pd.DataFrame:
    """
    binary_df columns required:
      - lookup_id  (status_binary_id)
      - value      (int-like or string that can be int)
    Adds/returns columns:
      - status (comma-separated string)
      - alert (bool)
    """

    if binary_df.empty:
        return binary_df

    # Avoid chained assignment issues
    binary_df = binary_df.copy()

    # Ensure value is int (nullable-safe)
    # If value may contain NaN/None, coerce to Int64 then fill with 0
    v = pd.to_numeric(binary_df["value"], errors="coerce").astype("Int64")
    binary_df["value_int"] = v

    # Create a stable row id so we can aggregate back later
    binary_df["_row_id"] = np.arange(len(binary_df), dtype=np.int64)

    # Decide how many bits to evaluate.
    # Best: derive from lookup table so you only compute bits that exist.
    # status_binary_df assumed cols: status_binary_id, bit_position,
    # description, state_true, state_false, nominal_state, failure_mode_id
    bits_per_lookup = (
        status_binary_df.groupby("status_binary_id")["bit_position"].max().astype(int)
        + 1
    )
    # Join max bit_position onto each row; default 0 if missing
    binary_df = binary_df.merge(
        bits_per_lookup.rename("n_bits"),
        how="left",
        left_on="lookup_id",
        right_index=True,
    )
    binary_df["n_bits"] = binary_df["n_bits"].fillna(0).astype(int)

    # Expand rows by bit_position (vectorized explode)
    # Build list of bit positions per row: range(n_bits)
    bit_pos_lists = binary_df["n_bits"].map(lambda n: list(range(n)) if n > 0 else [])
    exploded = binary_df.loc[
        binary_df["n_bits"] > 0, ["_row_id", "lookup_id", "value_int"]
    ].copy()
    exploded["bit_position"] = bit_pos_lists[binary_df["n_bits"] > 0].to_list()
    exploded = exploded.explode("bit_position", ignore_index=True)
    exploded["bit_position"] = exploded["bit_position"].astype(int)

    # Compute bit truth for each exploded row: (value >> bit_position) & 1
    # Handle NA values safely: if value_int is NA,
    # bit becomes NA -> treat as 0 (or drop)
    val_filled = exploded["value_int"].fillna(0).astype(np.int64)
    exploded["bit_truth"] = (
        np.right_shift(val_filled.to_numpy(), exploded["bit_position"].to_numpy()) & 1
    ).astype(bool)

    # Join the lookup metadata ONCE (fast)
    # Ensure the join keys match your schema naming
    merged = exploded.merge(
        status_binary_df,
        how="left",
        left_on=["lookup_id", "bit_position"],
        right_on=["status_binary_id", "bit_position"],
        suffixes=("", "_sb"),
    )

    # Drop missing matches early
    merged = merged[merged["description"].notna()].copy()

    # Filter out "reserved" descriptions (case-insensitive)
    desc_lower = merged["description"].astype(str).str.lower()
    merged = merged[desc_lower.ne("reserved")].copy()

    # Build final per-bit description with state_true/state_false appended
    # Choose suffix based on bit_truth
    true_suffix = merged["state_true"].where(merged["bit_truth"])
    false_suffix = merged["state_false"].where(~merged["bit_truth"])
    suffix = true_suffix.combine_first(false_suffix)

    # Only append ": <suffix>" when suffix is not null/empty
    suffix_str = suffix.astype("string")
    needs_suffix = suffix_str.notna() & (suffix_str.str.len() > 0)
    merged["desc_full"] = merged["description"].astype("string")
    merged.loc[needs_suffix, "desc_full"] = (
        merged.loc[needs_suffix, "desc_full"]
        .astype("string")
        .str.cat(suffix_str[needs_suffix].astype("string"), sep=": ")
    )

    # Alert per bit: nominal_state is not null AND bit_truth != nominal_state
    # Use nullable-aware comparison
    # nominal_state might be bool/0/1; coerce to boolean where present
    nominal = merged["nominal_state"]
    # Convert nominal to pandas boolean where possible
    nominal_bool = nominal.astype("boolean")
    merged["bit_alert"] = nominal_bool.notna() & (merged["bit_truth"] != nominal_bool)

    # Aggregate back to original rows
    agg = merged.groupby("_row_id", sort=False).agg(
        status=("desc_full", lambda s: list(s.dropna().astype(str))),
        alert=("bit_alert", "any"),
    )

    # Attach to binary_df
    binary_df = binary_df.merge(agg, how="left", left_on="_row_id", right_index=True)
    binary_df["status"] = binary_df["status"].apply(
        lambda x: x if isinstance(x, list) else []
    )
    binary_df["alert"] = binary_df["alert"].fillna(False).astype(bool)

    # Cleanup helper columns
    binary_df = binary_df.drop(
        columns=["_row_id", "value_int", "n_bits"], errors="ignore"
    )

    return binary_df


def _detect_binary_alerts(
    *, binary_df: pd.DataFrame, status_binary_df: pd.DataFrame
) -> pd.Series:
    """
    Returns a boolean Series aligned to binary_df.index indicating alert=True rows.
    """

    if binary_df.empty:
        return pd.Series(dtype=bool)

    binary_df = binary_df.copy()
    binary_df["_row_id"] = np.arange(len(binary_df), dtype=np.int64)

    # Prepare values
    val = pd.to_numeric(binary_df["value"], errors="coerce").fillna(0).astype(np.int64)

    # Determine bit ranges from lookup table
    max_bits = (
        status_binary_df.groupby("status_binary_id")["bit_position"].max().astype(int)
        + 1
    )
    binary_df = binary_df.merge(
        max_bits.rename("n_bits"),
        left_on="lookup_id",
        right_index=True,
        how="left",
    )
    binary_df["n_bits"] = binary_df["n_bits"].fillna(0).astype(int)

    # Explode bits
    exploded = binary_df.loc[binary_df["n_bits"] > 0, ["_row_id", "lookup_id"]].copy()
    exploded["bit_position"] = (
        binary_df.loc[binary_df["n_bits"] > 0, "n_bits"]
        .map(lambda n: list(range(n)))
        .to_list()
    )
    exploded = exploded.explode("bit_position", ignore_index=True)

    # Compute bit truth (fast numpy)
    vals = (
        val.loc[binary_df["n_bits"] > 0]
        .to_numpy()
        .repeat(exploded.groupby("_row_id").size().to_numpy())
    )
    bits = exploded["bit_position"].astype(np.int64).to_numpy()
    exploded["bit_truth"] = (np.right_shift(vals, bits) & 1).astype(bool)

    # Join minimal lookup columns
    merged = exploded.merge(
        status_binary_df[["status_binary_id", "bit_position", "nominal_state"]],
        left_on=["lookup_id", "bit_position"],
        right_on=["status_binary_id", "bit_position"],
        how="left",
    )

    # Compute bit alert
    nominal = merged["nominal_state"]
    nominal_bool = nominal.astype("boolean")
    merged["bit_alert"] = nominal_bool.notna() & (merged["bit_truth"] != nominal_bool)

    # Reduce back to rows
    alert_rows = merged.groupby("_row_id")["bit_alert"].any()

    return alert_rows.reindex(binary_df["_row_id"], fill_value=False)


def _to_frontend_status_payload(*, df: pd.DataFrame) -> list[dict]:
    """
    Input df columns expected (at minimum):
      - device_id
      - time
      - status  (list[str] per row)
      - alert (bool per row)

    Output:
      [
        {
          "device_id": ...,
          "statuses": [{"time": "...", "status": "..."}, ...]
        },
        ...
      ]
    """
    if df.empty:
        return []

    # Make sure we don't mutate caller df
    if "alert" not in df.columns:
        df = df.copy()
        df["alert"] = False

    df2 = df[["device_id", "time", "status", "alert"]].copy()

    def _normalize_device_id(*, raw: Any) -> int | None:
        """Convert device identifier to optional int for response payload."""
        if raw is None or pd.isna(raw):
            return None
        try:
            return int(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    # Ensure status is always a list (avoid NaN/None issues)
    df2["status"] = df2["status"].apply(lambda x: x if isinstance(x, list) else [])

    # Explode list[str] -> one row per status string
    exploded = df2.explode("status", ignore_index=True)

    # Drop rows where status is empty/null
    exploded = exploded[
        exploded["status"].notna() & (exploded["status"].astype(str).str.len() > 0)
    ].copy()

    # Sort statuses (newest first).
    exploded = exploded.sort_values(["device_id", "time"], ascending=[True, False])

    # Build the nested structure
    out = []
    for device_id, g in exploded.groupby("device_id", sort=False):
        normalized_id = _normalize_device_id(raw=device_id)
        out.append(
            {
                "device_id": normalized_id,
                "statuses": [
                    {
                        "time": t,
                        "status": s,
                        "status_type": "alert"
                        if (not pd.isna(a) and bool(a))
                        else "nominal",
                    }
                    for t, s, a in zip(
                        g["time"].tolist(),
                        g["status"].tolist(),
                        g["alert"].tolist(),
                    )
                ],
            }
        )

    return out


def _interpret_boolean_statuses(
    *, boolean_df: pd.DataFrame, status_boolean_df: pd.DataFrame
) -> pd.DataFrame:
    if boolean_df.empty:
        return boolean_df

    boolean_df = boolean_df.copy()

    # Parse boolean input from the coalesced "value" text column
    # Accepts: True/False, "true"/"false", "1"/"0", 1/0
    def _parse_bool(  # nosemgrep: python-enforce-keyword-only-args
        x: Any,
    ) -> bool | NAType:
        if pd.isna(x):
            return pd.NA
        if isinstance(x, bool):
            return x
        s = str(x).strip().lower()
        if s in ("true", "t", "1", "yes", "y"):
            return True
        if s in ("false", "f", "0", "no", "n"):
            return False
        return pd.NA

    boolean_df["value_bool"] = boolean_df["value"].map(_parse_bool).astype("boolean")

    # Join lookup row (1:1 by status_boolean_id)
    merged = boolean_df.merge(
        status_boolean_df,
        how="left",
        left_on="lookup_id",
        right_on="status_boolean_id",
        suffixes=("", "_sb"),
    )

    # Compute description based on input
    # If value_bool is NA, description becomes NA
    desc = pd.Series(pd.NA, index=merged.index, dtype="string")
    is_true = merged["value_bool"] == True
    is_false = merged["value_bool"] == False

    desc = desc.mask(is_true, merged["state_true"].astype("string"))
    desc = desc.mask(is_false, merged["state_false"].astype("string"))
    merged["desc_full"] = desc

    # Alert: nominal_state present and differs from input (NULL-safe)
    nominal = merged["nominal_state"]
    nominal_bool = nominal.astype("boolean")
    merged["alert"] = nominal_bool.notna() & (merged["value_bool"] != nominal_bool)

    # status as list[str]
    merged["status"] = merged["desc_full"].apply(
        lambda x: [str(x)] if pd.notna(x) and str(x).strip() else []
    )

    # Keep only the original columns + new ones we care about
    out = merged[boolean_df.columns.tolist() + ["status", "alert"]].copy()

    # Drop helper
    out = out.drop(columns=["value_bool"], errors="ignore")

    # Ensure types
    out["alert"] = out["alert"].fillna(False).astype(bool)

    return out


def _interpret_string_statuses(
    *, string_df: pd.DataFrame, status_string_df: pd.DataFrame
) -> pd.DataFrame:
    if string_df.empty:
        return string_df

    string_df = string_df.copy()

    # Ensure input is string
    string_df["value_str"] = string_df["value"].astype("string")

    # Prepare lookup frame: key is (status_string_id, string_trigger)
    lookup = status_string_df.copy()
    lookup["string_trigger"] = lookup["string_trigger"].astype("string")

    merged = string_df.merge(
        lookup,
        how="left",
        left_on=["lookup_id", "value_str"],  # lookup_id == status_string_id
        right_on=["status_string_id", "string_trigger"],  # match trigger
        suffixes=("", "_ss"),
    )

    merged["desc_full"] = merged["description"].astype("string")

    # alert if matched row has failure_mode_id
    merged["alert"] = merged["failure_mode_id"].notna()

    # status as list[str]
    merged["status"] = merged["desc_full"].apply(
        lambda x: [str(x)] if pd.notna(x) and str(x).strip() else []
    )

    out = merged[string_df.columns.tolist() + ["status", "alert"]].copy()
    out = out.drop(columns=["value_str"], errors="ignore")
    out["alert"] = out["alert"].fillna(False).astype(bool)

    return out
