"""Combiner correlation analysis: detect GIS/SCADA tag mismatches."""

import json
import os
import random
from dataclasses import dataclass
from itertools import combinations
from typing import Any, cast

import geopandas as gpd
import numpy as np
import pandas as pd
import psycopg2
from core.enumerations import DeviceTypeEnum as DeviceType
from core.enumerations import SensorTypeEnum as SensorType
from proximal_api import get_devices, get_project_metadata
from psycopg2 import sql
from scipy.spatial.distance import pdist, squareform
from shapely.geometry import shape

_METERS_PER_DEGREE = 111_000
_LOOKBACK_DAYS = 14
_COARSE_CANDIDATE_WINDOWS = 3
_MAX_VARIABILITY_WINDOWS = 3
_VARIABILITY_WINDOW = "30min"
_VARIABILITY_THRESHOLD_FRACTION = 0.20
_MIN_ANALYSIS_MINUTES = 90
_MIN_MEAN_VARIABILITY = 4.0
_MAX_ZERO_COUNT = 1
_SPATIAL_LAMBDA = 0.005


@dataclass(frozen=True)
class _CombinerAnalysisContext:
    project_name: str
    project_tz: str
    data_table: str
    device_id_list: list[int]
    gdf: gpd.GeoDataFrame


@dataclass(frozen=True)
class _VariableWindow:
    score: float
    day_label: str
    start_time: pd.Timestamp
    end_time: pd.Timestamp


def _devices_dataframe(*, devices: list[dict]) -> pd.DataFrame:
    """Build a device dataframe indexed by device ID.

    Args:
        devices: Device records from the operational API.

    Returns:
        Device dataframe with stable columns for empty API responses.
    """
    if not devices:
        return pd.DataFrame(
            columns=["device_type_id", "name_short", "device_id_path", "polygon"],
        ).rename_axis("device_id")

    return pd.DataFrame(devices).set_index("device_id", drop=True)


def _connection_string() -> str:
    conn = os.getenv("CONNECTION_STRING") or os.getenv("DATABASE_URL")
    if not conn:
        msg = "CONNECTION_STRING or DATABASE_URL must be set"
        raise ValueError(msg)
    return conn


def _read_sql_query(
    *,
    query: sql.Composable,
    params: tuple[Any, ...],
) -> pd.DataFrame:
    with psycopg2.connect(_connection_string()) as conn:
        query_string = query.as_string(conn)
        return cast(
            pd.DataFrame,
            pd.read_sql_query(
                query_string,
                cast(Any, conn),
                params=cast(Any, params),
            ),
        )


def _polygon_to_shape(*, polygon: Any) -> Any:
    if isinstance(polygon, dict):
        return shape(polygon)
    if isinstance(polygon, str):
        return shape(json.loads(polygon))
    return shape(polygon)


def _get_analysis_end_date(
    *,
    analysis_date: str | None,
    project_tz: str,
) -> pd.Timestamp:
    """Resolve the exclusive lookback end timestamp.

    Args:
        analysis_date: Lookback end day ``YYYY-MM-DD``.
        project_tz: Project timezone name.

    Returns:
        Exclusive end timestamp for the lookback query.
    """
    if analysis_date:
        try:
            return pd.to_datetime(analysis_date).tz_localize(
                project_tz
            ).normalize() + pd.Timedelta(days=1)
        except ValueError as exc:
            msg = "Invalid date format. Please use YYYY-MM-DD"
            raise ValueError(msg) from exc

    return pd.Timestamp.now(tz=project_tz).normalize() - pd.Timedelta(days=1)


def _get_combiner_analysis_context(
    *,
    project_id: str,
    block_name: str,
    project_info: dict | None = None,
    devices_df: pd.DataFrame | None = None,
) -> _CombinerAnalysisContext:
    """Fetch project metadata and combiner GIS locations for one block.

    Args:
        project_id: Project UUID.
        block_name: Block ``name_short``.
        project_info: Optional pre-fetched project metadata.
        devices_df: Optional pre-fetched block combiner devices.

    Returns:
        Context needed to query and analyze combiner data.
    """
    if project_info is None:
        project_info = get_project_metadata(project_id=project_id)
    project_name = project_info["name_short"]
    project_tz = project_info["time_zone"]
    data_table = project_info["data_table"]

    if devices_df is None:
        block_devices_df = _devices_dataframe(
            devices=get_devices(
                project_id=project_id,
                device_type_ids=[int(DeviceType.PV_BLOCK)],
                name_short=block_name,
            ),
        )
        if block_devices_df.empty:
            msg = f"Block '{block_name}' not found in project"
            raise ValueError(msg)

        block_device_id = int(block_devices_df.index[0])
        devices_df = _devices_dataframe(
            devices=get_devices(
                project_id=project_id,
                device_type_ids=[int(DeviceType.PV_DC_COMBINER)],
                device_id_descendent_of=block_device_id,
            ),
        )
    else:
        block_mask = (devices_df["name_short"] == block_name) & (
            devices_df["device_type_id"] == DeviceType.PV_BLOCK
        )
        if block_mask.any():
            block_path = str(devices_df.loc[block_mask, "device_id_path"].iloc[0])
            descendant_path = (
                devices_df["device_id_path"]
                .astype(str)
                .str.startswith(f"{block_path}.")
            )
            devices_df = devices_df.loc[descendant_path].copy()

    combiner_devices = devices_df.loc[
        devices_df["device_type_id"] == DeviceType.PV_DC_COMBINER
    ].copy()
    if combiner_devices.empty:
        msg = f"No combiner devices under block '{block_name}'"
        raise ValueError(msg)

    combiner_device_ids = combiner_devices.loc[
        combiner_devices["polygon"].notna() & (combiner_devices["polygon"] != "")
    ].copy()
    if combiner_device_ids.empty:
        msg = f"No combiner devices with GIS polygons under block '{block_name}'"
        raise ValueError(msg)

    device_id_list = [int(x) for x in combiner_device_ids.index.tolist()]

    combiner_device_ids.loc[:, "geometry"] = combiner_device_ids["polygon"].apply(
        lambda polygon: _polygon_to_shape(polygon=polygon),
    )
    gdf = gpd.GeoDataFrame(
        combiner_device_ids,
        geometry="geometry",
        crs="EPSG:4326",
    )

    return _CombinerAnalysisContext(
        project_name=project_name,
        project_tz=project_tz,
        data_table=data_table,
        device_id_list=device_id_list,
        gdf=gdf,
    )


def _fetch_combiner_timeseries(
    *,
    context: _CombinerAnalysisContext,
    table_name: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    resample_rule: str | None = None,
) -> pd.DataFrame:
    """Fetch combiner current timeseries for a date range.

    Args:
        context: Project/block analysis context.
        table_name: TSDB table to query.
        start_date: Inclusive start timestamp.
        end_date: Exclusive end timestamp.
        resample_rule: Optional pandas resample rule.

    Returns:
        Wide dataframe indexed by timestamp, columns are tag IDs.
    """
    query = sql.SQL(
        """
        SELECT
            time,
            tag_id,
            COALESCE(value_double, value_real, value_bigint, value_integer) AS value
        FROM tsdb.{schema}.{table}
        WHERE time < %s
          AND time >= %s
          AND tag_id IN (
              SELECT tag_id
              FROM tsdb.{schema}.tags
              WHERE sensor_type_id = %s
                AND device_id = ANY(%s)
          )
        ORDER BY time
        """
    ).format(
        schema=sql.Identifier(context.project_name),
        table=sql.Identifier(table_name),
    )

    df_records = _read_sql_query(
        query=query,
        params=(
            end_date,
            start_date,
            SensorType.PV_DC_COMBINER_CURRENT,
            context.device_id_list,
        ),
    )
    if df_records.empty:
        return pd.DataFrame()

    df_master = df_records.pivot(
        index="time",
        columns="tag_id",
        values="value",
    )
    df_master.index = pd.to_datetime(df_master.index).tz_convert(
        context.project_tz,
    )
    if resample_rule is None:
        return df_master.sort_index().ffill()
    return df_master.ffill().resample(resample_rule).mean().ffill()


def _fetch_coarse_combiner_timeseries(
    *,
    context: _CombinerAnalysisContext,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    """Fetch 5-minute combiner current data for variability ranking.

    Args:
        context: Project/block analysis context.
        start_date: Inclusive start timestamp.
        end_date: Exclusive end timestamp.

    Returns:
        Wide dataframe indexed by 5-minute bucket, columns are tag IDs.
    """
    query = sql.SQL(
        """
        SELECT
            time_bucket('5 minutes', time) AS time,
            tag_id,
            AVG(
                COALESCE(value_double, value_real, value_bigint, value_integer)
            ) AS value
        FROM tsdb.{schema}.{table}
        WHERE time < %s
          AND time >= %s
          AND tag_id IN (
              SELECT tag_id
              FROM tsdb.{schema}.tags
              WHERE sensor_type_id = %s
                AND device_id = %s
          )
        GROUP BY 1, tag_id
        ORDER BY 1
        """
    ).format(
        schema=sql.Identifier(context.project_name),
        table=sql.Identifier(context.data_table),
    )

    df_records = _read_sql_query(
        query=query,
        params=(
            end_date,
            start_date,
            SensorType.PV_DC_COMBINER_CURRENT,
            random.choice(context.device_id_list),
        ),
    )
    if df_records.empty:
        return pd.DataFrame()

    df_master = df_records.pivot(
        index="time",
        columns="tag_id",
        values="value",
    )
    df_master.index = pd.to_datetime(df_master.index).tz_convert(
        context.project_tz,
    )
    return df_master.sort_index()


def fetch_combiner_data(
    *,
    project_id: str,
    block_name: str,
    analysis_date: str | None = None,
    project_info: dict | None = None,
    devices_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, gpd.GeoDataFrame, list[dict]]:
    """Fetch selected high-resolution data and GIS locations for one block.

    Args:
        project_id: Project UUID.
        block_name: Block ``name_short``.
        analysis_date: Lookback end day ``YYYY-MM-DD``; defaults to yesterday.
        project_info: Optional pre-fetched project metadata.
        devices_df: Optional pre-fetched block combiner devices.

    Returns:
        Selected combiner current dataframe, combiner GeoDataFrame, warnings.
    """
    context = _get_combiner_analysis_context(
        project_id=project_id,
        block_name=block_name,
        project_info=project_info,
        devices_df=devices_df,
    )
    end_date = _get_analysis_end_date(
        analysis_date=analysis_date,
        project_tz=context.project_tz,
    )
    start_date = end_date - pd.Timedelta(days=_LOOKBACK_DAYS)
    coarse_df = _fetch_coarse_combiner_timeseries(
        context=context,
        start_date=start_date,
        end_date=end_date,
    )
    selected_windows, warnings = _find_variable_windows(
        data_df=coarse_df,
        enforce_min_mean_variability=False,
        max_windows=_COARSE_CANDIDATE_WINDOWS,
    )
    if not selected_windows:
        return pd.DataFrame(), context.gdf, warnings

    validated_windows: list[tuple[float, str, pd.DataFrame]] = []
    for window in selected_windows:
        fine_df = _fetch_combiner_timeseries(
            context=context,
            table_name=context.data_table,
            start_date=window.start_time,
            end_date=window.end_time,
        )
        validated_df, score, validation_warnings = _validate_prefiltered_window(
            data_df=fine_df,
            day_label=window.day_label,
        )
        warnings.extend(validation_warnings)
        if validated_df is not None:
            validated_windows.append((score, window.day_label, validated_df))

    if not validated_windows:
        warnings.append(
            {
                "all_tags": (
                    "No valid high-resolution windows found for "
                    "coarse-ranked variable windows"
                ),
            },
        )
        return pd.DataFrame(), context.gdf, warnings

    validated_windows.sort(key=lambda candidate: candidate[0], reverse=True)
    selected_valid_windows = validated_windows[:_MAX_VARIABILITY_WINDOWS]
    selected_labels = ", ".join(day_label for _, day_label, _ in selected_valid_windows)
    warnings.append(
        {
            "all_tags": (
                f"Using {len(selected_valid_windows)} high-resolution "
                f"window(s): {selected_labels}"
            ),
        },
    )

    return (
        pd.concat(
            [window_df for _, _, window_df in selected_valid_windows],
        ).sort_index(),
        context.gdf,
        warnings,
    )


def create_expected_correlation_matrix(
    *,
    gdf: gpd.GeoDataFrame,
    lambda_param: float = _SPATIAL_LAMBDA,
) -> np.ndarray:
    """Build expected correlation matrix from combiner GIS spacing.

    Args:
        gdf: Combiner locations.
        lambda_param: Exponential decay rate vs distance (meters).

    Returns:
        Expected correlation matrix.
    """
    centroids = np.array(
        [(geom.centroid.x, geom.centroid.y) for geom in gdf.geometry],
    )
    distance_matrix = squareform(pdist(centroids))
    if gdf.crs is not None and gdf.crs.is_geographic:
        distance_matrix = distance_matrix * _METERS_PER_DEGREE

    return cast(np.ndarray, np.exp(-lambda_param * distance_matrix))


def calculate_tse(*, data: pd.DataFrame, expected_corr_matrix: np.ndarray) -> float:
    """Total squared error between observed and expected correlation.

    Args:
        data: Combiner current time series (columns = tag ids).
        expected_corr_matrix: Spatial prior correlation matrix.

    Returns:
        Sum of squared differences.
    """
    obs_corr = data.corr().values
    delta = obs_corr - expected_corr_matrix
    return float(np.sum(delta**2))


def compute_tse_after_swap(
    *,
    data: pd.DataFrame,
    idx1: int,
    idx2: int,
    expected_corr_matrix: np.ndarray,
) -> float:
    """TSE if two column indices are swapped.

    Args:
        data: Combiner current time series.
        idx1: First column index.
        idx2: Second column index.
        expected_corr_matrix: Spatial prior correlation matrix.

    Returns:
        TSE after swap.
    """
    data_swapped = data.copy()
    data_swapped.iloc[:, [idx1, idx2]] = data_swapped.iloc[:, [idx2, idx1]]
    obs_corr_swapped = data_swapped.corr().values
    delta_swapped = obs_corr_swapped - expected_corr_matrix
    return float(np.sum(delta_swapped**2))


def _find_daily_variable_window(
    *,
    day_df: pd.DataFrame,
    day_label: str,
    enforce_min_mean_variability: bool = True,
) -> tuple[_VariableWindow | None, list[dict[str, str]]]:
    """Select one high-variability window from one day.

    Args:
        day_df: One day of combiner currents with positive row sums.
        day_label: Human-readable local date for warnings.
        enforce_min_mean_variability: Whether to apply final variability cutoff.

    Returns:
        Candidate window metadata and warning dicts.
    """
    warnings: list[dict[str, str]] = []
    total_current = day_df.sum(axis=1)
    max_current = total_current.max()
    if pd.isna(max_current) or max_current <= 0:
        warnings.append({day_label: "No positive combiner current data"})
        return None, warnings

    total_sum_normalized = total_current / max_current
    rolling_variability = (
        total_sum_normalized.diff()
        .abs()
        .rolling(window=_VARIABILITY_WINDOW, center=True)
        .sum()
    )

    max_variability = rolling_variability.max()
    if pd.isna(max_variability) or max_variability <= 0:
        warnings.append({day_label: "This day has no high-variability windows"})
        return None, warnings

    threshold = max_variability * _VARIABILITY_THRESHOLD_FRACTION
    above_threshold = rolling_variability >= threshold
    crossing_times = above_threshold[above_threshold.ne(above_threshold.shift())].index

    if len(crossing_times) < 3:
        warnings.append(
            {day_label: "This day has no high-variability windows"},
        )
        return None, warnings

    start_time = crossing_times[1]
    end_time = crossing_times[-1]
    filtered_df = day_df[start_time:end_time]
    if filtered_df.empty:
        warnings.append({day_label: "High-variability window has no data"})
        return None, warnings

    zero_count = int((filtered_df == 0).sum().sum())
    if zero_count > _MAX_ZERO_COUNT:
        warnings.append(
            {
                day_label: (
                    f"Too many zeroes in the data: {zero_count} "
                    f"(maximum allowed: {_MAX_ZERO_COUNT})"
                ),
            },
        )
        return None, warnings

    duration_minutes = (end_time - start_time).total_seconds() / 60
    if duration_minutes < _MIN_ANALYSIS_MINUTES:
        warnings.append(
            {
                day_label: (
                    f"Duration is too short: {duration_minutes:.1f} minutes "
                    f"(minimum required: {_MIN_ANALYSIS_MINUTES})"
                ),
            },
        )
        return None, warnings

    mean_variability = rolling_variability[start_time:end_time].mean()
    if enforce_min_mean_variability and mean_variability < _MIN_MEAN_VARIABILITY:
        warnings.append(
            {
                day_label: (
                    "Mean variability during most variable period is less than "
                    f"{_MIN_MEAN_VARIABILITY}"
                ),
            },
        )
        return None, warnings

    return (
        _VariableWindow(
            score=float(mean_variability),
            day_label=day_label,
            start_time=pd.Timestamp(start_time),
            end_time=pd.Timestamp(end_time),
        ),
        warnings,
    )


def _validate_prefiltered_window(
    *,
    data_df: pd.DataFrame,
    day_label: str,
) -> tuple[pd.DataFrame | None, float, list[dict[str, str]]]:
    """Validate one high-resolution window selected from coarse data.

    Args:
        data_df: High-resolution combiner currents for one candidate window.
        day_label: Human-readable local date for warnings.

    Returns:
        Valid dataframe, mean variability score, and warning dicts.
    """
    warnings: list[dict[str, str]] = []
    if data_df.empty:
        warnings.append({day_label: "High-resolution window has no data"})
        return None, 0.0, warnings

    tag_ids = data_df.columns.tolist()
    data_df = data_df[data_df.sum(axis=1) > 0]
    data_df = data_df[sorted(tag_ids)]
    if data_df.empty:
        warnings.append({day_label: "No positive combiner current data"})
        return None, 0.0, warnings

    zero_count = int((data_df == 0).sum().sum())
    if zero_count > _MAX_ZERO_COUNT:
        warnings.append(
            {
                day_label: (
                    f"Too many zeroes in the data: {zero_count} "
                    f"(maximum allowed: {_MAX_ZERO_COUNT})"
                ),
            },
        )
        return None, 0.0, warnings

    duration_minutes = (data_df.index.max() - data_df.index.min()).total_seconds() / 60
    if duration_minutes < _MIN_ANALYSIS_MINUTES:
        warnings.append(
            {
                day_label: (
                    f"Duration is too short: {duration_minutes:.1f} minutes "
                    f"(minimum required: {_MIN_ANALYSIS_MINUTES})"
                ),
            },
        )
        return None, 0.0, warnings

    total_current = data_df.sum(axis=1)
    max_current = total_current.max()
    if pd.isna(max_current) or max_current <= 0:
        warnings.append({day_label: "No positive combiner current data"})
        return None, 0.0, warnings

    total_sum_normalized = total_current / max_current
    rolling_variability = (
        total_sum_normalized.diff()
        .abs()
        .rolling(window=_VARIABILITY_WINDOW, center=True)
        .sum()
    )
    mean_variability = rolling_variability.mean()
    if mean_variability < _MIN_MEAN_VARIABILITY:
        warnings.append(
            {
                day_label: (
                    "Mean variability during most variable period is less than "
                    f"{_MIN_MEAN_VARIABILITY}"
                ),
            },
        )
        return None, 0.0, warnings

    return data_df, float(mean_variability), warnings


def _find_variable_windows(
    *,
    data_df: pd.DataFrame,
    enforce_min_mean_variability: bool = True,
    max_windows: int = _MAX_VARIABILITY_WINDOWS,
) -> tuple[list[_VariableWindow], list[dict]]:
    """Rank top high-variability windows.

    Args:
        data_df: Combiner currents across the configured lookback range.
        enforce_min_mean_variability: Whether to apply final variability cutoff.
        max_windows: Maximum number of windows to select.

    Returns:
        Selected window metadata and warning dicts.
    """
    warnings: list[dict[str, str]] = []
    tag_ids = data_df.columns.tolist()
    data_df = data_df[data_df.sum(axis=1) > 0]
    data_df = data_df[sorted(tag_ids)]
    if data_df.empty:
        warnings.append(
            {
                "all_tags": (
                    "No positive combiner current data found across the "
                    f"{_LOOKBACK_DAYS}-day lookback"
                ),
            },
        )
        return [], warnings

    candidates: list[_VariableWindow] = []
    normalized_index = pd.DatetimeIndex(data_df.index).normalize()
    for day_start, day_df in data_df.groupby(normalized_index):
        day_label = cast(pd.Timestamp, day_start).strftime("%Y-%m-%d")
        candidate, candidate_warnings = _find_daily_variable_window(
            day_df=day_df,
            day_label=day_label,
            enforce_min_mean_variability=enforce_min_mean_variability,
        )
        warnings.extend(candidate_warnings)
        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        warnings.append(
            {
                "all_tags": (
                    "No valid high-variability windows found across the "
                    f"{_LOOKBACK_DAYS}-day lookback"
                ),
            },
        )
        return [], warnings

    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    selected_candidates = candidates[:max_windows]
    if len(selected_candidates) < max_windows:
        warnings.append(
            {
                "all_tags": (
                    f"Only {len(selected_candidates)} valid high-variability "
                    f"window(s) found; using all available windows"
                ),
            },
        )

    selected_labels = ", ".join(
        candidate.day_label for candidate in selected_candidates
    )
    warnings.append(
        {
            "all_tags": (
                f"Using {len(selected_candidates)} high-variability window(s): "
                f"{selected_labels}"
            ),
        },
    )

    return selected_candidates, warnings


def _find_cloudy_window(*, data_df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Select top high-variability windows for correlation analysis.

    Args:
        data_df: Combiner currents across the configured lookback range.

    Returns:
        Concatenated top-window dataframe and warning dicts.
    """
    selected_windows, warnings = _find_variable_windows(data_df=data_df)
    if not selected_windows:
        return data_df.iloc[0:0], warnings

    return (
        pd.concat(
            [
                data_df[window.start_time : window.end_time]
                for window in selected_windows
            ],
        ).sort_index(),
        warnings,
    )


def _find_correction_swaps(
    *,
    filtered_df: pd.DataFrame,
    expected_corr_matrix: np.ndarray,
) -> list[tuple[int, int]]:
    """Greedy swap search minimizing correlation TSE.

    Args:
        filtered_df: Cloudy-window combiner data.
        expected_corr_matrix: Spatial prior correlation matrix.

    Returns:
        List of ``(tag_id, tag_id)`` swap pairs.
    """
    tag_ids = [int(tag_id) for tag_id in filtered_df.columns.tolist()]
    current_df = filtered_df.copy()
    correction_swaps: list[tuple[int, int]] = []

    while True:
        current_tse = calculate_tse(
            data=current_df,
            expected_corr_matrix=expected_corr_matrix,
        )
        tse_results = [
            (
                compute_tse_after_swap(
                    data=current_df,
                    idx1=idx1,
                    idx2=idx2,
                    expected_corr_matrix=expected_corr_matrix,
                ),
                idx1,
                idx2,
            )
            for idx1, idx2 in combinations(range(len(tag_ids)), 2)
        ]
        best_tse, best_idx1, best_idx2 = min(tse_results, key=lambda x: x[0])

        if best_tse < current_tse:
            best_swap = (tag_ids[best_idx1], tag_ids[best_idx2])
            current_df = current_df.rename(
                columns={
                    best_swap[0]: best_swap[1],
                    best_swap[1]: best_swap[0],
                },
            )
            current_df = current_df[sorted(tag_ids)]
            correction_swaps.append(best_swap)
        else:
            break

    return correction_swaps


def analyze_project_combiners(
    *,
    project_id: str,
    analysis_date: str | None = None,
    block_names: list[str] | None = None,
) -> dict[str, dict[str, list]]:
    """Analyze blocks and return suggested SCADA tag swaps per block.

    Args:
        project_id: Project UUID.
        analysis_date: Day to analyze ``YYYY-MM-DD``.
        block_names: Optional block ``name_short`` list; all blocks if omitted.

    Returns:
        ``{block_name: {swaps: [(tag_id, tag_id), ...], warnings: [...]}}``.
    """
    project_info = get_project_metadata(project_id=project_id)
    project_name = project_info["name_short"]

    if analysis_date is not None:
        try:
            pd.to_datetime(analysis_date)
        except ValueError as exc:
            msg = "Invalid date format. Please use YYYY-MM-DD"
            raise ValueError(msg) from exc

    block_devices_df = _devices_dataframe(
        devices=get_devices(
            project_id=project_id,
            device_type_ids=[int(DeviceType.PV_BLOCK)],
        ),
    )
    all_block_names = block_devices_df["name_short"].tolist()

    if block_names is None:
        block_devices = all_block_names
        if not block_devices:
            msg = f"No block devices found in project '{project_name}'"
            raise ValueError(msg)
    else:
        block_devices = [name for name in block_names if name in all_block_names]
        if not block_devices:
            msg = (
                f"None of the specified block names "
                f"({', '.join(block_names)}) were found in the project"
            )
            raise ValueError(msg)

    results_dict: dict[str, dict[str, list]] = {}

    for block_name in block_devices:
        try:
            block_device_id = int(
                block_devices_df.loc[
                    block_devices_df["name_short"] == block_name
                ].index[0],
            )
            devices_df = _devices_dataframe(
                devices=get_devices(
                    project_id=project_id,
                    device_type_ids=[int(DeviceType.PV_DC_COMBINER)],
                    device_id_descendent_of=block_device_id,
                ),
            )
            data_df, gdf, coarse_warnings = fetch_combiner_data(
                project_id=project_id,
                block_name=block_name,
                analysis_date=analysis_date,
                project_info=project_info,
                devices_df=devices_df,
            )
            swaps: list[tuple[int, int]] = []
            if not data_df.empty and len(data_df.columns) >= 2:
                expected_corr_matrix = create_expected_correlation_matrix(gdf=gdf)
                swaps = _find_correction_swaps(
                    filtered_df=data_df,
                    expected_corr_matrix=expected_corr_matrix,
                )
            results_dict[block_name] = {
                "swaps": swaps,
                "warnings": coarse_warnings,
            }
        except Exception as exc:
            results_dict[block_name] = {
                "swaps": [],
                "warnings": [{"all_tags": f"Error during analysis: {exc}"}],
            }

    return results_dict
