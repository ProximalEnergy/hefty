"""Build detector context using read-only core data access."""

import asyncio
import datetime
import logging

import polars as pl

import core
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.database import with_db
from core.enumerations import AggregationMethod, OutputType, TimeInterval, TimeOffset
from issues.models.detector_context import (
    DetectorContext,
    MetStationChannel,
    TelemetryPoint,
)

LOGGER = logging.getLogger(__name__)


def build_detector_context(
    *,
    project_id: str,
    project_name_short: str,
    run_time: datetime.datetime,
    device_type_ids: tuple[int, ...],
    sensor_type_ids: tuple[int, ...],
    telemetry_window_minutes: int,
    expected_interval_minutes_default: int,
) -> DetectorContext:
    """Build normalized detector context from read-only core queries."""
    LOGGER.info(
        "\t\tBuilding detector context for project_id=%s project_name_short=%s",
        project_id,
        project_name_short,
    )
    tags = _load_tags(
        project_name_short=project_name_short,
        device_type_ids=device_type_ids,
        sensor_type_ids=sensor_type_ids,
    )
    channels = _build_channels_from_tags(
        tags=tags,
        default_interval=expected_interval_minutes_default,
    )
    telemetry = _load_telemetry(
        project_name_short=project_name_short,
        tags=tags,
        run_time=run_time,
        window_minutes=telemetry_window_minutes,
    )
    LOGGER.info(
        "\t\t\tDetector context built project_id=%s tags=%d channels=%d telemetry_keys=%d",
        project_id,
        tags.height,
        len(channels),
        len(telemetry),
    )
    return DetectorContext(
        project_id=project_id,
        run_time=run_time,
        met_station_channels=tuple(channels),
        telemetry_by_channel=telemetry,
    )


def _load_tags(
    *,
    project_name_short: str,
    device_type_ids: tuple[int, ...],
    sensor_type_ids: tuple[int, ...],
) -> pl.DataFrame:
    """Load detector tag metadata from project tables."""
    if not device_type_ids and not sensor_type_ids:
        LOGGER.info(
            "\t\tSkipping tag load because no device/sensor filters were provided"
        )
        return pl.DataFrame()
    tags = core.crud.project.tags.get_project_tags_v2(
        device_type_ids=list(device_type_ids),
        sensor_type_ids=list(sensor_type_ids),
        include_ghost_tags=False,
        deep=False,
    ).get(
        output_type=OutputType.POLARS,
        schema=project_name_short,
    )
    LOGGER.info(
        "\t\tLoaded tags for project_name_short=%s rows=%d",
        project_name_short,
        tags.height,
    )
    return tags


def _build_channels_from_tags(
    *,
    tags: pl.DataFrame,
    default_interval: int,
) -> list[MetStationChannel]:
    """Convert met-station tags into detector channel definitions."""
    if tags.is_empty():
        LOGGER.info("\t\tNo tags available for channel construction")
        return []

    channels: list[MetStationChannel] = []
    unique_rows = tags.select(["device_id", "tag_id"]).unique()
    for row in unique_rows.iter_rows(named=True):
        tag_id = row["tag_id"]
        device_id = row["device_id"]
        if tag_id is None or device_id is None:
            continue
        channels.append(
            MetStationChannel(
                device_id=int(device_id),
                tag_id=int(tag_id),
                expected_interval_minutes=default_interval,
            )
        )
    LOGGER.info("\t\t\tBuilt %d detector channels", len(channels))
    return channels


def _load_telemetry(
    *,
    project_name_short: str,
    tags: pl.DataFrame,
    run_time: datetime.datetime,
    window_minutes: int,
) -> dict[tuple[int, int | None], tuple[TelemetryPoint, ...]]:
    """Load telemetry points from project data_timeseries using core helpers."""
    if tags.is_empty():
        LOGGER.info("\t\tSkipping telemetry load because tags dataframe is empty")
        return {}

    window_start = run_time - datetime.timedelta(minutes=window_minutes)
    query_end = run_time + datetime.timedelta(microseconds=1)
    LOGGER.info(
        "\t\tLoading telemetry for project_name_short=%s window_start=%s "
        "window_end=%s",
        project_name_short,
        window_start.isoformat(),
        run_time.isoformat(),
    )
    with with_db(schema=project_name_short) as project_db:
        data_timeseries = asyncio.run(
            DataTimeseries(
                project_name_short=project_name_short,
                filter_method=FilterMethod.TAG_POLARS,
                filter_values=tags,
                query_start=window_start,
                query_end=query_end,
                project_db=project_db,
                max_lookback_period=TimeOffset.NONE,
                freq=TimeInterval.FIVE_MINUTES,
                aggregation_method=AggregationMethod.FIRST,
                ffill_limit=0,
                ensure_full_range=False,
            ).get()
        )
    telemetry = _telemetry_points_from_timeseries(df=data_timeseries.df, tags=tags)
    LOGGER.info(
        "\t\t\tLoaded telemetry rows=%d channels=%d",
        data_timeseries.df.height,
        len(telemetry),
    )
    return telemetry


def _telemetry_points_from_timeseries(
    *,
    df: pl.DataFrame,
    tags: pl.DataFrame,
) -> dict[tuple[int, int | None], tuple[TelemetryPoint, ...]]:
    """Convert wide-format timeseries output into per-channel telemetry points."""
    if df.is_empty():
        LOGGER.info("\t\tTelemetry dataframe is empty after query")
        return {}

    time_col = "time" if "time" in df.columns else "time_bucket"
    tag_to_device: dict[int, int] = {}
    for row in tags.select(["tag_id", "device_id"]).iter_rows(named=True):
        tag_id = row["tag_id"]
        device_id = row["device_id"]
        if tag_id is None or device_id is None:
            continue
        tag_to_device[int(tag_id)] = int(device_id)

    points: dict[tuple[int, int | None], list[TelemetryPoint]] = {}
    for column in df.columns:
        if column == time_col:
            continue
        try:
            tag_id = int(column)
        except (TypeError, ValueError):
            continue
        device_id = tag_to_device.get(tag_id)
        if device_id is None:
            continue
        key = (device_id, tag_id)
        column_df = df.select([time_col, column])
        for row in column_df.iter_rows(named=True):
            point_time = row[time_col]
            if point_time is None:
                continue
            raw_value = row[column]
            points.setdefault(key, []).append(
                TelemetryPoint(
                    device_id=device_id,
                    tag_id=tag_id,
                    time=point_time,
                    value=None if raw_value is None else str(raw_value),
                )
            )

    finalized: dict[tuple[int, int | None], tuple[TelemetryPoint, ...]] = {}
    for key, key_points in points.items():
        finalized[key] = tuple(sorted(key_points, key=lambda point: point.time))
    LOGGER.info(
        "\t\t\tConverted telemetry dataframe into %d channel key sets",
        len(finalized),
    )
    return finalized
