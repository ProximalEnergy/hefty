"""Detector for met station non-communication conditions."""

import datetime
import logging
import math
from decimal import Decimal, InvalidOperation

import pandas as pd
from pvlib import solarposition

from issues.config.issue_detectors import MetStationNonCommunicatingConfig
from issues.models.detector_context import DetectorContext, TelemetryPoint
from issues.models.issue_candidate import IssueCandidate, IssueIdentity

LOGGER = logging.getLogger(__name__)


class MetStationNonCommunicatingDetector:
    """Emit candidates when met-station telemetry is mostly absent."""

    def __init__(
        self,
        *,
        issue_category_id: int,
        config: MetStationNonCommunicatingConfig,
    ) -> None:
        self.name = config.detector_name
        self._config = config
        self._issue_category_id = issue_category_id

    def detect(
        self,
        *,
        context: DetectorContext,
    ) -> list[IssueCandidate]:
        """Detect met station channels that appear non-communicating."""
        candidates: list[IssueCandidate] = []
        window_start = context.run_time - datetime.timedelta(
            minutes=self._config.evaluation_window_minutes
        )
        LOGGER.info(
            "Analyzing met station communication window start=%s end=%s",
            window_start.isoformat(),
            context.run_time.isoformat(),
        )
        for channel in context.met_station_channels:
            if channel.latitude is None or channel.longitude is None:
                LOGGER.info(
                    "Skipping channel with unresolved coordinates "
                    "device_id=%s tag_id=%s",
                    channel.device_id,
                    channel.tag_id,
                )
                continue
            daylight_schedule = self._daylight_schedule_times(
                run_time=context.run_time,
                window_start=window_start,
                expected_interval_minutes=channel.expected_interval_minutes,
                latitude=channel.latitude,
                longitude=channel.longitude,
            )
            if not daylight_schedule:
                LOGGER.info(
                    "Skipping indeterminate nighttime window device_id=%s tag_id=%s "
                    "start=%s end=%s",
                    channel.device_id,
                    channel.tag_id,
                    window_start.isoformat(),
                    context.run_time.isoformat(),
                )
                continue
            expected = len(daylight_schedule)
            points = context.get_channel_points(
                device_id=channel.device_id,
                tag_id=channel.tag_id,
            )
            present_count, latest_point = self._present_samples(
                points=points,
                window_start=window_start,
                latitude=channel.latitude,
                longitude=channel.longitude,
            )
            missing_count = max(0, expected - present_count)
            missing_ratio = missing_count / expected
            if (
                missing_count < self._config.minimum_missing_samples_to_open
                or missing_ratio < self._config.open_missing_ratio_threshold
            ):
                continue
            metadata = {
                "detector_name": self.name,
                "evaluation_window_minutes": (self._config.evaluation_window_minutes),
                "expected_samples": expected,
                "present_samples": present_count,
                "missing_samples": missing_count,
                "missing_ratio": round(missing_ratio, 4),
                "daylight_threshold_apparent_elevation_degrees": (
                    self._config.daylight_apparent_elevation_threshold_degrees
                ),
                "latest_sample_time": (
                    latest_point.isoformat() if latest_point else None
                ),
            }
            candidates.append(
                IssueCandidate(
                    project_id=context.project_id,
                    detector_name=self.name,
                    identity=IssueIdentity(
                        device_id=channel.device_id,
                        tag_id=channel.tag_id,
                        issue_category_id=self._issue_category_id,
                    ),
                    time_start=window_start,
                    detector_metadata=metadata,
                )
            )
        return candidates

    def _daylight_schedule_times(
        self,
        *,
        run_time: datetime.datetime,
        window_start: datetime.datetime,
        expected_interval_minutes: int,
        latitude: float,
        longitude: float,
    ) -> tuple[datetime.datetime, ...]:
        """Build daytime schedule timestamps for expected sample counting."""
        interval = max(1, expected_interval_minutes)
        window = self._config.evaluation_window_minutes
        expected = max(1, math.ceil(window / interval))
        schedule = [
            window_start + datetime.timedelta(minutes=offset * interval)
            for offset in range(expected)
        ]
        daytime_mask = self._is_daytime_timestamps(
            timestamps=tuple(schedule),
            latitude=latitude,
            longitude=longitude,
        )
        return tuple(
            timestamp
            for timestamp, is_daytime in zip(schedule, daytime_mask, strict=True)
            if is_daytime and timestamp <= run_time
        )

    def _present_samples(
        self,
        *,
        points: tuple[TelemetryPoint, ...],
        window_start: datetime.datetime,
        latitude: float,
        longitude: float,
    ) -> tuple[int, datetime.datetime | None]:
        present_count = 0
        latest_point: datetime.datetime | None = None
        daytime_lookup = self._build_daytime_lookup(
            points=points,
            latitude=latitude,
            longitude=longitude,
        )
        for point in points:
            if point.time < window_start:
                continue
            if not daytime_lookup.get(point.time, False):
                continue
            if latest_point is None or point.time > latest_point:
                latest_point = point.time
            if _is_non_communicating_value(value=point.value):
                continue
            present_count += 1
        return present_count, latest_point

    def _build_daytime_lookup(
        self,
        *,
        points: tuple[TelemetryPoint, ...],
        latitude: float,
        longitude: float,
    ) -> dict[datetime.datetime, bool]:
        if not points:
            return {}
        timestamps = tuple(point.time for point in points)
        is_daytime = self._is_daytime_timestamps(
            timestamps=timestamps,
            latitude=latitude,
            longitude=longitude,
        )
        return dict(zip(timestamps, is_daytime, strict=True))

    def _is_daytime_timestamps(
        self,
        *,
        timestamps: tuple[datetime.datetime, ...],
        latitude: float,
        longitude: float,
    ) -> tuple[bool, ...]:
        if not timestamps:
            return ()
        normalized_timestamps: list[datetime.datetime] = []
        for timestamp in timestamps:
            if timestamp.tzinfo is None:
                normalized_timestamps.append(timestamp.replace(tzinfo=datetime.UTC))
            else:
                normalized_timestamps.append(timestamp)
        time_index = pd.DatetimeIndex(normalized_timestamps)
        if time_index.tz is None:
            msg = "pvlib daytime evaluation requires timezone-aware timestamps"
            raise ValueError(msg)
        solar = solarposition.get_solarposition(
            time=time_index,
            latitude=latitude,
            longitude=longitude,
        )
        threshold = self._config.daylight_apparent_elevation_threshold_degrees
        return tuple(solar["apparent_elevation"] > threshold)


def _is_non_communicating_value(*, value: str | None) -> bool:
    """Return whether a telemetry value should count as absent."""
    if value is None:
        return True
    stripped = value.strip()
    if stripped == "":
        return True
    try:
        parsed = Decimal(stripped)
    except InvalidOperation:
        return False
    return parsed.is_finite() and parsed == 0
