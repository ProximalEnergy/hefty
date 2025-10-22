from typing import Any

import pandas as pd
import polars as pl
import polars.selectors as cs
from polars.datatypes import Boolean, String

from core import models
from core.model_list import ModelList

NUM_DTYPES = cs.numeric()
BOOL_DTYPES = cs.boolean()
TXT_DTYPES = cs.string()


def canon_time(df_part: pl.DataFrame, *, like: pl.DataFrame) -> pl.DataFrame:
    """Make df_part['time'] exactly match like['time'] in unit and timezone."""
    ref_dt = like.schema["time"]

    # Handle case where time column is Null (empty or all null values)
    if isinstance(ref_dt, pl.Null):
        return df_part

    if not isinstance(ref_dt, pl.Datetime):
        raise TypeError(f"Expected Datetime, got {type(ref_dt)}")

    ref_unit = ref_dt.time_unit  # "us" or "ns"
    ref_tz = ref_dt.time_zone  # e.g. "UTC", "America/Chicago", or None

    cur_dt = df_part.schema["time"]

    # Handle case where current time column is Null
    if isinstance(cur_dt, pl.Null):
        return df_part

    if not isinstance(cur_dt, pl.Datetime):
        raise TypeError(f"Expected Datetime, got {type(cur_dt)}")
    cur_tz = cur_dt.time_zone

    out = df_part.with_columns(pl.col("time").dt.cast_time_unit(ref_unit))

    # Align timezone
    if ref_tz is None:
        # We want tz-naive in the output.
        if cur_tz is not None:
            # Convert to UTC first (any tz works), then drop tz info (tag as naive)
            out = out.with_columns(
                pl.col("time").dt.convert_time_zone("UTC").dt.replace_time_zone(None)
            )
        # else already naive
    else:
        # We want tz-aware with ref_tz
        if cur_tz is None:
            # Current is naive: *tag* with ref_tz (no clock shift)
            out = out.with_columns(pl.col("time").dt.replace_time_zone(ref_tz))
        elif cur_tz != ref_tz:
            # Current has a different tz: *convert* (preserve instant, shift clock)
            out = out.with_columns(pl.col("time").dt.convert_time_zone(ref_tz))

    return out


## Polars implementation which removes the nullable tags
def pivot_timeseries_by_tag_polars(
    *,
    df: pl.DataFrame,
    tags: ModelList[models.Tag] | pl.DataFrame,
    project_timezone: str,
) -> Any:
    """
    Pivot a long-format timeseries DataFrame with multiple value_* columns
    into a wide-format DataFrame indexed by time and with tag_id columns.

    Each tag_id is expected to use only one of the value_* columns.

    Args:
        df: Timeseries data in long format
        tags: Either an executed ModelList of Tag models or a polars DataFrame with
             columns:
              tag_id, unit_scale, and unit_offset
            Prefer Polars DataFrames for better performance.
        project_timezone: Timezone for the output time column
    """

    value_cols = [c for c in df.columns if c.startswith("value_")]
    if not value_cols:
        return df.select("time").unique().sort("time")

    # Convert tags to polars DataFrame if it's a ModelList
    if isinstance(tags, ModelList):
        tags_lut = pl.DataFrame(
            {
                "tag_id": [t.tag_id for t in tags],
                "unit_scale": [t.unit_scale for t in tags],
                "unit_offset": [t.unit_offset for t in tags],
            },
            schema={
                "tag_id": df.schema["tag_id"],
                "unit_scale": pl.Float64,
                "unit_offset": pl.Float64,
            },
            strict=False,  # coerce where possible
            infer_schema_length=None,  # (optional) scan all rows
        ).with_columns(
            pl.col("unit_scale").fill_null(1.0),
            pl.col("unit_offset").fill_null(0.0),
        )
    else:
        # Assume it's already a polars DataFrame
        tags_lut = tags.with_columns(
            pl.col("unit_scale").fill_null(1.0),
            pl.col("unit_offset").fill_null(0.0),
        )

    order_lut = pl.DataFrame(
        {"vcol": value_cols, "vorder": list(range(len(value_cols)))}
    )

    ldf = df.lazy()

    long = ldf.unpivot(
        index=["time", "tag_id"],
        on=value_cols,
        variable_name="vcol",
        value_name="val",
    )

    chosen_vcol = (
        long.group_by(["tag_id", "vcol"])
        .agg(pl.col("val").is_not_null().any().alias("has_any"))
        .filter(pl.col("has_any"))
        .join(order_lut.lazy(), on="vcol", how="left")
        .sort(["tag_id", "vorder"])
        .group_by("tag_id")
        .agg(pl.col("vcol").first().alias("vcol"))
    )

    filtered = long.join(chosen_vcol, on=["tag_id", "vcol"], how="inner")

    # Determine which value columns are numeric, boolean, or text
    df_schema = df.schema
    num_cols = [c for c in value_cols if df_schema[c].is_numeric()]
    bool_cols = [c for c in value_cols if isinstance(df_schema[c], Boolean)]
    txt_cols = [c for c in value_cols if isinstance(df_schema[c], String)]

    # ---- numeric path (apply scale/offset) ----
    if num_cols:
        numeric_filtered = filtered.filter(pl.col("vcol").is_in(num_cols))
        numeric_wide = (
            numeric_filtered.join(tags_lut.lazy(), on="tag_id", how="left")
            .with_columns(
                (
                    pl.col("val").cast(pl.Float64, strict=False)
                    * pl.col("unit_scale").fill_null(1.0)
                    + pl.col("unit_offset").fill_null(0.0)
                ).alias("val_adj")
            )
            .select(["time", "tag_id", "val_adj"])
            .collect(engine="streaming")
            .pivot(
                index="time",
                on="tag_id",
                values="val_adj",
                aggregate_function="first",
            )
        )
    else:
        numeric_wide = None

    # ---- boolean path (keep bools) ----
    if bool_cols:
        bool_wide = (
            filtered.filter(pl.col("vcol").is_in(bool_cols))
            .with_columns(pl.col("val").cast(pl.Boolean).alias("val_adj"))
            .select(["time", "tag_id", "val_adj"])
            .collect(engine="streaming")
            .pivot(
                index="time",
                on="tag_id",
                values="val_adj",
                aggregate_function="first",
            )
        )
    else:
        bool_wide = None

    # ---- text path (keep strings) ----
    if txt_cols:
        text_wide = (
            filtered.filter(pl.col("vcol").is_in(txt_cols))
            .with_columns(pl.col("val").cast(pl.Utf8).alias("val_adj"))
            .select(["time", "tag_id", "val_adj"])
            .collect(engine="streaming")
            .pivot(
                index="time",
                on="tag_id",
                values="val_adj",
                aggregate_function="first",
            )
        )
    else:
        text_wide = None

    # ---- combine (full join on time), then timezone convert ----
    # Start from an empty frame with all unique times so that full joins align cleanly:
    times = df.select("time").unique()

    # Handle empty dataframe or null time column
    if times.is_empty() or isinstance(times.schema["time"], pl.Null):
        return times

    wide = canon_time(times, like=times)

    for part in [numeric_wide, bool_wide, text_wide]:
        if part is None or part.is_empty():
            continue
        part = canon_time(part, like=times)
        wide = (
            wide.join(part, on="time", how="full", suffix="_r").drop(
                "time_r", strict=False
            )  # defensive in case a mismatch sneaks in
        )

    wide = wide.sort("time").with_columns(
        pl.col("time").dt.convert_time_zone(project_timezone)
    )

    return wide


def pivot_timeseries_by_tag(
    *,
    df: pd.DataFrame,
    tags: ModelList[models.Tag] | None,
) -> pd.DataFrame:
    """
    Pivot a long-format timeseries DataFrame with multiple value_* columns
    into a wide-format DataFrame indexed by time and with tag_id columns.

    Each tag_id is expected to use only one of the value_* columns.
    """

    if tags is None:
        raise ValueError("tags must be provided")

    # Ensure DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Expected DataFrame index to be a tz-aware DatetimeIndex.")

    value_cols = [col for col in df.columns if col.startswith("value_")]
    tag_groups = {}

    # Determine which value column each tag_id uses (based on first non-null row)
    for tag_id, group in df.groupby("tag_id"):
        for col in value_cols:
            if group[col].notna().any():
                tag_groups[tag_id] = col
                break
        else:
            tag_groups[tag_id] = ""  # no usable value column

    # Build a list of (tag_id, series) pairs
    series_list = []
    for tag_id, col in tag_groups.items():
        if (col is None) or (col == ""):
            continue  # skip tags with no data
        tag = tags.find(tag_id=tag_id)[0]
        tag_series = df[df["tag_id"] == tag_id][col].rename(tag_id)
        if tag.unit_scale is not None:
            tag_series = tag_series * tag.unit_scale
        if tag.unit_offset is not None:
            tag_series = tag_series + tag.unit_offset
        series_list.append(tag_series)

    # Combine all series into a single DataFrame
    if not series_list:
        return pd.DataFrame(index=df.index)

    result = pd.concat(series_list, axis=1)

    # Ensure correct index (in case some tag series are missing timestamps)
    result = result.sort_index().reindex(df.index).groupby(df.index).first()

    return result
