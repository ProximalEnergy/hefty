import pandas as pd
import polars.selectors as cs

from core import models
from core.model_list import ModelList

NUM_DTYPES = cs.numeric()
BOOL_DTYPES = cs.boolean()
TXT_DTYPES = cs.string()


def pivot_timeseries_by_tag(
    *,
    df: pd.DataFrame,
    tags: ModelList[models.Tag] | None,
) -> pd.DataFrame:
    """Pivot a long-format timeseries DataFrame with multiple value_* columns
        into a wide-format DataFrame indexed by time and with tag_id columns.

        Each tag_id is expected to use only one of the value_* columns.

    Args:
        df: Long-format pandas timeseries with tag_id and value_* columns.
        tags: Tag metadata used for unit scaling and offsets.
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
