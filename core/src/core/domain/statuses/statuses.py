from __future__ import annotations

import datetime
import math
from typing import Literal, SupportsInt, cast

import core.crud.project.statuses as crud_statuses
import numpy as np
import pandas as pd
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import TimeInterval
from pandas.api.extensions import ExtensionDtype
from sqlalchemy.orm import Session

from core import models

StatusKind = Literal["binary", "boolean", "string"]

# Define nullable types for each PG data type
PG_DATA_TYPES: dict[int, ExtensionDtype] = {
    1: pd.Int32Dtype(),
    2: pd.Int64Dtype(),
    3: pd.Float32Dtype(),
    4: pd.Float64Dtype(),
    5: pd.BooleanDtype(),
    6: pd.StringDtype(),
}
_TRUTHY = {"true", "1", "yes", "y"}
_FALSY = {"false", "0", "no", "n"}

FACT_COLUMNS = [
    "time",
    "tag_id",
    "status_kind",
    "field_key",  # bit_position for binary, else <NA>
    "observed_bool",  # bool for binary/boolean, else <NA>
    "observed_str",  # trigger for string, else <NA>
    "raw_value",  # original value (int/bool/str), optional but useful
    "resolved_state",  # state_true/state_false or string description
    "description",  # binary/boolean description (optional)
    "nominal_state",  # bool for binary/boolean, else <NA>
    "is_nominal",  # bool for binary/boolean, else <NA>
    "failure_mode_id",  # nullable int
]


def _empty_facts_df() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in FACT_COLUMNS})


def parse_maybe_int(val):  # no-star-syntax
    """
    Convert:
      - ints -> ints
      - floats like 3.0 -> 3 (but keep NaN)
      - strings like '0x8800' / '0X8800' -> int base 16
      - strings like '123' -> int base 10
      - other values -> pd.NA (or return original if you prefer)

    Args:
        val: The value to convert to an integer, if possible.
    """
    if val is None or val is pd.NA:
        return pd.NA

    # Preserve missing floats
    if isinstance(val, (float, np.floating)):
        if math.isnan(val):
            return pd.NA
        # Only coerce clean integer floats
        if val.is_integer():
            return int(val)
        return pd.NA

    if isinstance(val, (int, bool, np.integer, np.bool_)):
        return int(val)

    if isinstance(val, str):
        s = val.strip()
        if not s:
            return pd.NA

        # Hex detection: 0x...
        if s.lower().startswith("0x"):
            try:
                return int(s, 16)
            except ValueError:
                return pd.NA

        # Decimal integer detection
        try:
            # int('0012') works; int('12.0') doesn't, so handle '12.0' cleanly:
            if "." in s:
                f = float(s)
                return int(f) if f.is_integer() else pd.NA
            return int(s, 10)
        except ValueError:
            return pd.NA

    # Anything else: bytes, dicts, etc.
    return pd.NA


async def get_status_timeseries_interpreted(
    *,
    project_db: Session,
    project: models.Project,
    start: datetime.datetime,
    end: datetime.datetime,
    tag_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
    sensor_type_ids: list[int] | None = None,
    get_all: bool = False,
    freq: TimeInterval = TimeInterval.FIVE_MINUTES,
):
    """Get data_timeseries entries for statuses with filters.

    Args:
        project: The project to get the status_timeseries_data for.
        tag_ids: Filter to only included tag_ids.
        device_ids: Filter to only included device_ids.
        sensor_type_ids: Filter to only included sensor_type_ids.
        start: Filter to only included start.
        end: Filter to only included end.
        get_all: Whether to retrieve all data rows instead of aggregated rows.
        freq: Timeseries aggregation interval.
    """
    get_status_tags_query = crud_statuses.get_status_tags(
        tag_ids=tag_ids,
        sensor_type_ids=sensor_type_ids,
        device_ids=device_ids,
    )
    status_tags_pl = await get_status_tags_query.get_async(
        schema=project.name_short,
        output_type=OutputType.POLARS,
    )
    status_tags = status_tags_pl.to_pandas().set_index("tag_id")
    data_query = DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=status_tags_pl,
        freq=freq,
        query_start=start,
        query_end=end,
        project_db=project_db,
    )
    if get_all:
        data_df = (await data_query.get_all()).df.to_pandas()
    else:
        data_df = (await data_query.get()).df.to_pandas()

    # Early return for no data
    if data_df.empty:
        return []

    # Clean the data_df
    data_df = data_df.set_index("time")
    data_df.index = pd.to_datetime(data_df.index).tz_convert(project.time_zone)
    data_df.columns = data_df.columns.astype(int)

    # Strictly type the data_df columns
    for key, dtype in PG_DATA_TYPES.items():
        cols = status_tags.index[status_tags["pg_data_type_id"] == key]
        if len(cols):
            data_df[cols] = data_df[cols].astype(dtype)

    status_tables = await crud_statuses.get_status_lookup(
        status_lookup_ids=status_tags["status_lookup_id"].unique().tolist(),
    ).get_async(output_type=OutputType.PANDAS)
    status_tables = status_tables.set_index("status_lookup_id")
    binary_df = pd.DataFrame()
    string_df = pd.DataFrame()
    boolean_df = pd.DataFrame()
    mapping_types = [
        "status_binary_id",
        "status_string_id",
        "status_boolean_id",
    ]
    ## Split into binary, string, and boolean dataframes
    for col in mapping_types:
        status_tags[col] = status_tags["status_lookup_id"].map(status_tables[col])
        match col:
            case "status_binary_id":
                binary_df = data_df[
                    status_tags[pd.notna(status_tags[col])].index.tolist()
                ].copy()
                # Do not convert to binary strings.
                # This happens in the interpret_binary_sparse_uint function.
            case "status_string_id":
                string_df = data_df[
                    status_tags[pd.notna(status_tags[col])].index.tolist()
                ].copy()
                # Convert all values to strings. This is because even if a value
                # comes in as a number, the lookup table is trying to
                # match it to a string.
                string_df = string_df.astype(pd.StringDtype())
            case "status_boolean_id":
                boolean_df = data_df[
                    status_tags[pd.notna(status_tags[col])].index.tolist()
                ].copy()
                # Convert "truthy" values to True, "falsy" values to False,
                # and NA to None
                boolean_df = normalize_truthy_falsy_df(df=boolean_df)

    ## Retrieve interpretation tables
    binary_table = pd.DataFrame()
    string_table = pd.DataFrame()
    boolean_table = pd.DataFrame()
    if not binary_df.empty:
        binary_table = await crud_statuses.get_status_binary(
            status_binary_ids=status_tags["status_binary_id"]
            .dropna()
            .unique()
            .tolist(),
        ).get_async(output_type=OutputType.PANDAS)

    if not string_df.empty:
        string_table = await crud_statuses.get_status_string(
            status_string_ids=status_tags["status_string_id"]
            .dropna()
            .unique()
            .tolist(),
        ).get_async(output_type=OutputType.PANDAS)

    if not boolean_df.empty:
        boolean_table = await crud_statuses.get_status_boolean(
            status_boolean_ids=status_tags["status_boolean_id"]
            .dropna()
            .unique()
            .tolist(),
        ).get_async(output_type=OutputType.PANDAS)

    # Interpret to sparse facts
    binary_facts = (
        interpret_binary_sparse_uint(
            binary_str_df=binary_df,
            status_tags=status_tags,
            binary_table=binary_table,
            pad_len=32,
            chunksize=100_000,  # tune for memory
        )
        if not binary_df.empty
        else _empty_facts_df()
    )

    boolean_facts = (
        interpret_boolean_sparse(
            boolean_df=boolean_df,
            status_tags=status_tags,
            boolean_table=boolean_table,
        )
        if not boolean_df.empty
        else _empty_facts_df()
    )

    string_facts = (
        interpret_string_sparse(
            string_df=string_df,
            status_tags=status_tags,
            string_table=string_table,
        )
        if not string_df.empty
        else _empty_facts_df()
    )

    facts = unify_status_facts(
        binary_facts=binary_facts,
        boolean_facts=boolean_facts,
        string_facts=string_facts,
    )

    # Return as records for your API (flexible + compact)
    return facts.replace(np.nan, None).to_dict(orient="records")


async def get_status_time_series_failure_mode_ids(
    *,
    project_db: Session,
    project: models.Project,
    start: datetime.datetime,
    end: datetime.datetime,
    tag_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
    sensor_type_ids: list[int] | None = None,
    device_type_ids: list[int] | None = None,
    get_all: bool = False,
):
    """Fetch failure mode IDs for status tags over a time range.

    Args:
        project_db: SQLAlchemy session for the project database.
        project: The project model instance whose schema is queried.
        start: Start of the time range (inclusive).
        end: End of the time range (inclusive).
        tag_ids: Optional list of tag IDs to filter by.
        device_ids: Optional list of device IDs to filter by.
        sensor_type_ids: Optional list of sensor type IDs to filter by.
        device_type_ids: Optional list of device type IDs to filter by.
        get_all: When True, return all records regardless of other filters.

    Returns:
        A list of records as dicts containing time-series failure mode data.
    """
    get_status_tags_query = crud_statuses.get_status_tags(
        device_ids=device_ids,
        sensor_type_ids=sensor_type_ids,
        tag_ids=tag_ids,
        device_type_ids=device_type_ids,
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
    if tag_ids is None or len(tag_ids) == 0:
        return []
    data = await get_status_timeseries_interpreted(
        project_db=project_db,
        project=project,
        tag_ids=tag_ids,
        start=start,
        end=end,
        get_all=get_all,
    )
    if len(data) == 0:
        return []
    df = pd.DataFrame(data).loc[:, ["time", "tag_id", "failure_mode_id"]].copy()
    df = df.sort_values(by=["time", "tag_id"])
    wide = (
        df.groupby(["time", "tag_id"], sort=False)["failure_mode_id"]
        .first()
        .unstack("tag_id")
    )
    wide = wide.reindex(columns=tag_ids)
    wide = wide.reset_index().rename(columns={"time": "index"}).replace(np.nan, None)
    return wide.to_dict(orient="records")


########################################################
# DATA CONVERSIONS
########################################################


def df_to_reversed_binary_strings(
    df: pd.DataFrame,
    pad_len: int = 32,
    *,
    chunksize: int | None = None,
) -> pd.DataFrame:
    """
    Convert integer-like DataFrame values to reversed (LSB-first) binary strings,
    right-padded with zeros to `pad_len`.

    Example: 66 -> '01000010000000000000000000000000' (pad_len=32)

    Args:
        df: DataFrame of integer-like values to convert.
        pad_len: Number of bits to include (right-padded with zeros).
        chunksize: Rows to process per chunk; ``None`` processes all at once.

    Notes:
      - Preserves NA as <NA> (pandas StringDtype).
      - Assumes values fit in unsigned 32-bit when pad_len <= 32.
      - For very large df, set chunksize to limit peak RAM.
    """
    if pad_len <= 0:
        raise ValueError("pad_len must be > 0")
    if pad_len > 32:
        raise ValueError("pad_len > 32 not supported in this uint32 implementation.")

    nrows, ncols = df.shape
    out = pd.DataFrame(
        {
            column: pd.Series(pd.NA, index=df.index, dtype="string")
            for column in df.columns
        },
        index=df.index,
    )

    # Work row-chunked to control memory: unpackbits makes an (rows*cols, 32) array.
    if chunksize is None:
        chunksize = nrows  # single chunk

    for r0 in range(0, nrows, chunksize):
        r1 = min(r0 + chunksize, nrows)

        # Pull chunk as float64 so we can carry NaN mask easily.
        # (Works for pandas nullable ints too.)
        a = df.iloc[r0:r1].to_numpy(dtype="float64", copy=False)
        mask = np.isfinite(a)  # True where we have a value (not NaN)

        if not mask.any():
            continue

        # Flatten the present values and cast to uint32.
        vals = a[mask].astype(np.uint32, copy=False)

        # Unpack bits LSB-first (little-endian) into shape (N, 32)
        bits32 = np.unpackbits(
            vals.view(np.uint8).reshape(-1, 4),
            axis=1,
            bitorder="little",
        )
        bits = bits32[:, :pad_len]  # (N, pad_len)

        # Turn 0/1 into ASCII '0'/'1' and view each row as a fixed-width byte string.
        # This is the fast "no Python loop" conversion step.
        ascii_bytes = (bits + ord("0")).astype(np.uint8, copy=False)
        byte_strings = np.ascontiguousarray(ascii_bytes).view(f"|S{pad_len}").ravel()
        str_values = byte_strings.astype("U")  # numpy unicode array

        # Place back into a chunk-shaped object array, keeping NA where missing.
        chunk_obj = np.empty(a.shape, dtype=object)
        chunk_obj[:] = pd.NA
        chunk_obj[mask] = str_values

        out.iloc[r0:r1] = chunk_obj

    return out


def normalize_truthy_falsy_df(*, df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert mixed dtype values into a pandas nullable boolean DataFrame.

    Args:
        df: DataFrame with mixed-dtype values to normalise.

    Truthy:
      True, "true", "1", 1, "yes", "y"
    Falsy:
      False, "false", "0", 0, "no", "n"
    Missing / unknown -> <NA>

    Returns dtype="boolean" (pandas BooleanDtype).
    """
    # Start with all <NA> output (nullable boolean)
    out = pd.DataFrame(
        {
            column: pd.Series(pd.NA, index=df.index, dtype="boolean")
            for column in df.columns
        },
        index=df.index,
    )

    # --- 1) Handle real booleans / pandas BooleanDtype quickly ---
    # This catches columns already boolean-ish.
    bool_like_cols = df.columns[df.dtypes.astype(str).isin(["bool", "boolean"])]
    if len(bool_like_cols):
        out[bool_like_cols] = df[bool_like_cols].astype("boolean")

    # Remaining columns
    other_cols = df.columns.difference(bool_like_cols)
    if len(other_cols) == 0:
        return out

    sub = df[other_cols]

    # --- 2) Handle numeric values: only 0/1 are accepted ---
    # Use to_numeric (vectorized) with errors="coerce" to get NaN for non-numeric.
    # This is done on the whole subframe at once.
    numeric = sub.apply(pd.to_numeric, errors="coerce")

    # valid numeric locations (not NaN)
    num_mask = numeric.notna()

    # Only treat exactly 0 or 1 as valid boolean signals
    is_one = num_mask & (numeric == 1)
    is_zero = num_mask & (numeric == 0)

    # Write them into output
    if is_one.any().any():
        out.loc[:, other_cols] = out.loc[:, other_cols].mask(is_one, True)
    if is_zero.any().any():
        out.loc[:, other_cols] = out.loc[:, other_cols].mask(is_zero, False)

    # --- 3) Handle strings/objects: normalize case/whitespace ---
    # Convert to pandas string dtype (nullable), lowercase, strip.
    s = sub.astype("string").apply(lambda col: col.str.strip().str.lower())

    truthy_mask = s.isin(_TRUTHY)
    falsy_mask = s.isin(_FALSY)

    # Apply string-based mapping, but don't override numeric decisions already set.
    # (If something is both numeric and string-ish, numeric already handled above.)
    if truthy_mask.any().any():
        out.loc[:, other_cols] = out.loc[:, other_cols].mask(truthy_mask, True)
    if falsy_mask.any().any():
        out.loc[:, other_cols] = out.loc[:, other_cols].mask(falsy_mask, False)

    return out


########################################################
# INTERPRETATION LOGIC
########################################################


def interpret_boolean_sparse(
    *,
    boolean_df: pd.DataFrame,  # dtype "boolean" preferred
    status_tags: pd.DataFrame,  # index tag_id
    boolean_table: pd.DataFrame,  # status_boolean_id definitions
) -> pd.DataFrame:
    """
    Sparse facts for boolean tags:
      emit where observed != nominal_state (and nominal_state not null).

    Args:
        boolean_df: Wide boolean observations (dtype ``boolean`` preferred),
            indexed by time with tag IDs as columns.
        status_tags: Tag metadata DataFrame indexed by ``tag_id``,
            must include a ``status_boolean_id`` column.
        boolean_table: Definition table keyed by ``status_boolean_id`` with
            ``nominal_state``, ``state_true``, ``state_false``, ``description``,
            and ``failure_mode_id`` columns.
    """
    if boolean_df.empty or boolean_table.empty:
        return _empty_facts_df()

    # Map tag_id -> status_boolean_id
    tag_map = (
        status_tags[["status_boolean_id"]]
        .dropna()
        .astype({"status_boolean_id": "int64"})
        .reset_index()  # tag_id column
    )

    defs = boolean_table.copy()
    defs["status_boolean_id"] = defs["status_boolean_id"].astype("int64", copy=False)

    tag_defs = tag_map.merge(defs, on="status_boolean_id", how="left")

    # Align defs to boolean_df columns order
    tag_defs = tag_defs.set_index("tag_id").reindex(boolean_df.columns)
    nominal = tag_defs["nominal_state"]  # may include NaN/None
    desc = tag_defs["description"]
    st_false = tag_defs["state_false"]
    st_true = tag_defs["state_true"]
    failure_mode = tag_defs["failure_mode_id"]

    # numpy arrays for vectorized compare
    arr = boolean_df.to_numpy(dtype="object", copy=False)  # True/False/<NA>
    obs_mask = pd.notna(arr)  # True where observed is not NA

    # Only evaluate where nominal_state is not null too
    nominal_arr = nominal.to_numpy(dtype="object", copy=False)
    nominal_mask_cols = pd.notna(nominal_arr)  # per-column mask
    if not nominal_mask_cols.any():
        return _empty_facts_df()

    # Broadcast nominal_mask_cols across rows
    valid = obs_mask & nominal_mask_cols[None, :]

    # Extract observed bools
    # (safe because valid implies notna)
    obs_bool = arr[valid].astype(bool, copy=False)

    # Compare to nominal (broadcast 1D nominal per column to full grid; cannot use
    # nominal_arr[None, :] which is shape (1, n_cols) with a (n_rows, n_cols) mask)
    nominal_2d = np.broadcast_to(nominal_arr, arr.shape)
    nom_bool = nominal_2d[valid].astype(bool, copy=False)
    non_nominal = obs_bool != nom_bool
    if not np.any(non_nominal):
        return _empty_facts_df()

    # Indices in flattened valid array
    # We need row/col indices where valid & non_nominal.
    row_idx, col_idx = np.where(valid)
    row_idx = row_idx[non_nominal]
    col_idx = col_idx[non_nominal]

    times = boolean_df.index.to_numpy()
    tags = boolean_df.columns.to_numpy()

    obs = arr[row_idx, col_idx].astype(bool, copy=False)
    nom = nominal_arr[col_idx].astype(bool, copy=False)

    # resolved_state from state_true/state_false
    st_t = st_true.to_numpy(dtype="object", copy=False)[col_idx]
    st_f = st_false.to_numpy(dtype="object", copy=False)[col_idx]
    resolved = np.where(obs, st_t, st_f)

    out = pd.DataFrame(
        {
            "time": times[row_idx],
            "tag_id": tags[col_idx],
            "status_kind": "boolean",
            "field_key": pd.NA,
            "observed_bool": obs,
            "observed_str": pd.NA,
            "raw_value": obs,  # you could also keep original pre-normalized if desired
            "resolved_state": resolved,
            "description": desc.to_numpy(dtype="object", copy=False)[col_idx],
            "nominal_state": nom,
            "is_nominal": False,
            "failure_mode_id": failure_mode.to_numpy(dtype="object", copy=False)[
                col_idx
            ],
        }
    )

    return out


def interpret_string_sparse(
    *,
    string_df: pd.DataFrame,  # dtype "string"
    status_tags: pd.DataFrame,  # index tag_id
    string_table: pd.DataFrame,  # status_string_id definitions
) -> pd.DataFrame:
    """
    Sparse facts for string tags:
      emit only when the matched mapping row has failure_mode_id not null.

    Args:
        string_df: Wide string observations (dtype ``string``), indexed by time
            with tag IDs as columns.
        status_tags: Tag metadata DataFrame indexed by ``tag_id``,
            must include a ``status_string_id`` column.
        string_table: Definition table keyed by ``status_string_id`` with
            ``string_trigger``, ``description``, and ``failure_mode_id`` columns.
    """
    if string_df.empty or string_table.empty:
        return _empty_facts_df()

    # tag_id -> status_string_id
    tag_map = (
        status_tags[["status_string_id"]]
        .dropna()
        .astype({"status_string_id": "int64"})
        .reset_index()
    )

    defs = string_table.copy()
    defs["status_string_id"] = defs["status_string_id"].astype("int64", copy=False)

    # Longify observations (this is the one place we "stack"; it’s still vectorized)
    stacked_strings = cast(pd.Series, string_df.astype("string").stack()).dropna()
    obs = (
        stacked_strings.rename("string_trigger")
        .reset_index()
        .rename(columns={"level_0": "time", "level_1": "tag_id"})
    )

    if obs.empty:
        return _empty_facts_df()

    obs = obs.merge(tag_map, on="tag_id", how="left")

    # Join to definitions on (status_string_id, trigger)
    merged = obs.merge(
        defs,
        on=["status_string_id", "string_trigger"],
        how="left",
        suffixes=("", "_def"),
    )

    # Sparse rule: only when the mapped row has failure_mode_id
    merged = merged[pd.notna(merged["failure_mode_id"])].copy()
    if merged.empty:
        return _empty_facts_df()

    out = pd.DataFrame(
        {
            "time": merged["time"].to_numpy(),
            "tag_id": merged["tag_id"].to_numpy(),
            "status_kind": "string",
            "field_key": pd.NA,
            "observed_bool": pd.NA,
            "observed_str": merged["string_trigger"].astype("string").to_numpy(),
            "raw_value": merged["string_trigger"].astype("string").to_numpy(),
            "resolved_state": merged[
                "description"
            ].to_numpy(),  # string-table description is the meaning
            "description": merged["description"].to_numpy(),
            "nominal_state": pd.NA,
            "is_nominal": pd.NA,
            "failure_mode_id": merged["failure_mode_id"].to_numpy(),
        }
    )
    return out


def interpret_binary_sparse_uint(
    *,
    binary_str_df: pd.DataFrame,
    # expects <=32 bits if pad_len=32
    status_tags: pd.DataFrame,  # index tag_id
    binary_table: pd.DataFrame,  # status_binary_id definitions
    pad_len: int = 32,
    chunksize: int | None = None,
) -> pd.DataFrame:
    """
    Sparse facts for binary tags:
      - decode bits LSB-first (bitorder='little')
      - join definitions by (tag_id -> status_binary_id, bit_position)
      - emit where observed_bit != nominal_state (and nominal_state not null)

    Args:
        binary_str_df: Wide DataFrame of integer-like binary values, indexed by
            time with tag IDs as columns.
        status_tags: Tag metadata DataFrame indexed by ``tag_id``,
            must include a ``status_binary_id`` column.
        binary_table: Definition table keyed by ``status_binary_id`` with
            ``bit_position``, ``nominal_state``, ``description``, and
            ``failure_mode_id`` columns.
        pad_len: Number of bits to decode per value (max 32).
        chunksize: Rows to process per chunk; ``None`` processes all at once.

    This does NOT require you to convert ints -> reversed strings first.
    """
    coerced_binary = binary_str_df.map(lambda value: parse_maybe_int(val=value))
    binary_int_df = coerced_binary.astype("Int64")
    if binary_int_df.empty or binary_table.empty:
        return _empty_facts_df()
    if pad_len <= 0:
        raise ValueError("pad_len must be > 0")
    if pad_len > 32:
        raise ValueError("pad_len > 32 not supported in this uint32 decoder.")

    # Build tag-bit definitions (one row per (tag_id, bit_position))
    tag_map = (
        status_tags[["status_binary_id"]]
        .dropna()
        .astype({"status_binary_id": "int64"})
        .reset_index()
    )

    defs = binary_table.copy()
    defs["status_binary_id"] = defs["status_binary_id"].astype("int64", copy=False)

    tag_bits = tag_map.merge(defs, on="status_binary_id", how="left")
    # Only keep bits within pad_len
    tag_bits = tag_bits[
        (tag_bits["bit_position"] >= 0) & (tag_bits["bit_position"] < pad_len)
    ].copy()
    if tag_bits.empty:
        return _empty_facts_df()

    # Group definitions by bit_position for efficient slicing
    by_bit: dict[int, pd.DataFrame] = {}
    for bit_position, group in tag_bits.groupby("bit_position", sort=False):
        by_bit[int(cast(SupportsInt, bit_position))] = group.set_index("tag_id")

    nrows, ncols = binary_int_df.shape
    times = binary_int_df.index.to_numpy()
    tags = binary_int_df.columns.to_numpy()

    # Precompute tag_id -> column index
    col_index = pd.Index(binary_int_df.columns)
    out_frames: list[pd.DataFrame] = []

    if chunksize is None:
        chunksize = nrows

    for r0 in range(0, nrows, chunksize):
        r1 = min(r0 + chunksize, nrows)

        # Get chunk as float64 to preserve NaN for missing
        a = binary_int_df.iloc[r0:r1].to_numpy(dtype="float64", copy=False)
        present = np.isfinite(a)
        if not present.any():
            continue

        # Decode bits for ALL present values in the chunk
        # Flatten present values, decode to bits,
        # then we will place into (rows*cols, 32) layout by using masks.
        # We'll instead decode the full chunk by filling missing
        # with 0 and masking later (faster / simpler).
        filled = np.where(present, a, 0.0).astype(
            np.uint32, copy=False
        )  # shape (rows, cols)

        bits32 = np.unpackbits(
            filled.reshape(-1).view(np.uint8).reshape(-1, 4),
            axis=1,
            bitorder="little",
        )[:, :pad_len]  # shape (rows*cols, pad_len)

        # Also flatten present mask for filtering later
        present_flat = present.reshape(-1)

        # Now for each bit_position that has definitions, slice and emit sparse facts
        for bp, defs_bp in by_bit.items():
            # columns to consider for this bit
            cols_for_bit = defs_bp.index.intersection(col_index)
            if cols_for_bit.empty:
                continue

            col_idx = col_index.get_indexer(cols_for_bit)  # positions in binary_int_df
            if np.any(col_idx < 0):
                col_idx = col_idx[col_idx >= 0]
                if col_idx.size == 0:
                    continue

            # Build flattened indices into bits32 for these columns
            # For chunk of rows m = (r1-r0), flat index = row*m_cols + col
            m = r1 - r0
            # Create all (row, col) pairs via broadcasting: (m, k)
            # We’ll compute flat indices and then slice bits32[:, bp]
            rows = np.arange(m, dtype=np.int64)[:, None]
            cols = col_idx[None, :].astype(np.int64, copy=False)
            flat_idx = (rows * ncols + cols).reshape(-1)

            # Only keep those that were present (not NA in original)
            pres = present_flat[flat_idx]
            if not np.any(pres):
                continue
            flat_idx = flat_idx[pres]

            obs_bit = bits32[flat_idx, bp].astype(bool, copy=False)

            # Map flat_idx back to (row_in_chunk, col)
            row_in_chunk = (flat_idx // ncols).astype(np.int64, copy=False)
            col_in_df = (flat_idx % ncols).astype(np.int64, copy=False)

            # nominal per tag for this bit
            # defs_bp is indexed by tag_id, aligned to cols_for_bit
            defs_aligned = defs_bp.reindex(binary_int_df.columns[col_in_df])
            nominal = defs_aligned["nominal_state"].to_numpy(dtype="object", copy=False)
            nom_mask = pd.notna(nominal)
            if not np.any(nom_mask):
                continue

            # Filter to where nominal is known
            obs_bit = obs_bit[nom_mask]
            row_in_chunk = row_in_chunk[nom_mask]
            col_in_df = col_in_df[nom_mask]
            nominal_bool = nominal[nom_mask].astype(bool, copy=False)

            # Sparse: observed != nominal
            non_nom = obs_bit != nominal_bool
            if not np.any(non_nom):
                continue

            obs_bit = obs_bit[non_nom]
            row_in_chunk = row_in_chunk[non_nom]
            col_in_df = col_in_df[non_nom]
            nominal_bool = nominal_bool[non_nom]

            # Resolve state strings
            st_t = defs_aligned["state_true"].to_numpy(dtype="object", copy=False)[
                nom_mask
            ][non_nom]
            st_f = defs_aligned["state_false"].to_numpy(dtype="object", copy=False)[
                nom_mask
            ][non_nom]
            resolved = np.where(obs_bit, st_t, st_f)

            desc = defs_aligned["description"].to_numpy(dtype="object", copy=False)[
                nom_mask
            ][non_nom]
            fm = defs_aligned["failure_mode_id"].to_numpy(dtype="object", copy=False)[
                nom_mask
            ][non_nom]

            raw_vals = filled[row_in_chunk, col_in_df]  # uint32 raw within this chunk

            out_frames.append(
                pd.DataFrame(
                    {
                        "time": times[r0:r1][row_in_chunk],
                        "tag_id": tags[col_in_df],
                        "status_kind": "binary",
                        "field_key": bp,
                        "observed_bool": obs_bit,
                        "observed_str": pd.NA,
                        "raw_value": raw_vals,
                        "resolved_state": resolved,
                        "description": desc,
                        "nominal_state": nominal_bool,
                        "is_nominal": False,
                        "failure_mode_id": fm,
                    }
                )
            )

    if not out_frames:
        return _empty_facts_df()

    return pd.concat(out_frames, ignore_index=True)


def unify_status_facts(
    *,
    binary_facts: pd.DataFrame | None = None,
    boolean_facts: pd.DataFrame | None = None,
    string_facts: pd.DataFrame | None = None,
) -> pd.DataFrame:
    frames = [
        f
        for f in [binary_facts, boolean_facts, string_facts]
        if f is not None and not f.empty
    ]
    if not frames:
        return _empty_facts_df()

    out = pd.concat(frames, ignore_index=True)

    # Ensure all columns exist (defensive)
    for c in FACT_COLUMNS:
        if c not in out.columns:
            out[c] = pd.NA
    out = out[FACT_COLUMNS]

    # Sort for nicer downstream use
    out = out.sort_values(
        ["time", "tag_id", "status_kind", "field_key"], kind="mergesort"
    ).reset_index(drop=True)
    return out
