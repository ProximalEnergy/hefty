from typing import Any

import pandas as pd
import polars as pl
from sqlalchemy import text
from sqlalchemy.orm import Session

from core import models
from core.model_list import ModelList


## Polars implementation which removes the nullable tags
def pivot_timeseries_by_tag_polars(
    *,
    df: pl.DataFrame,
    tags: ModelList[models.Tag],
    project: models.Project,
) -> Any:
    """
    Pivot a long-format timeseries DataFrame with multiple value_* columns
    into a wide-format DataFrame indexed by time and with tag_id columns.

    Each tag_id is expected to use only one of the value_* columns.
    """

    value_cols = [c for c in df.columns if c.startswith("value_")]
    if not value_cols:
        return df.select("time").unique().sort("time")

    tag_dtype = df.schema["tag_id"]

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

    order_lut = pl.DataFrame(
        {"vcol": value_cols, "vorder": list(range(len(value_cols)))}
    )

    ldf = df.lazy()

    long = ldf.melt(
        id_vars=["time", "tag_id"],
        value_vars=value_cols,
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

    adjusted = (
        filtered.join(tags_lut.lazy(), on="tag_id", how="left")
        .with_columns(
            (
                pl.col("val").cast(pl.Float64, strict=False)
                * pl.col("unit_scale").cast(pl.Float64, strict=False)
                + pl.col("unit_offset").cast(pl.Float64, strict=False)
            ).alias("val_adj")
        )
        .select(["time", "tag_id", "val_adj"])
    )

    adjusted_unique = adjusted.group_by(["time", "tag_id"]).agg(
        pl.col("val_adj").first().alias("val_adj")
    )

    adjusted_df = adjusted_unique.collect(streaming=True)  # type: ignore

    wide = (
        adjusted_df.pivot(
            index="time",
            columns="tag_id",
            values="val_adj",
            aggregate_function="first",
        )
        .sort("time")
        # ---- Convert UTC -> project local time ----
        .with_columns(pl.col("time").dt.convert_time_zone(project.time_zone))
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


def get_table_columns(
    db: Session, *, table_name: str, schema: str = "operational"
) -> list[str]:
    stmt = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :tablename
          AND table_schema = :schemaname
        ORDER BY ordinal_position
    """
    cols = db.execute(text(stmt).bindparams(tablename=table_name, schemaname=schema))
    return [col[0] for col in cols]
