"""Detector for POA tilt sensors that do not match tracker position."""

import datetime
import logging
import math
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import pandas as pd
from core.enumerations import SensorTypeEnum
from pvlib import solarposition, tracking

from issues.config.issue_detectors import PoaSensorOutOfPositionConfig
from issues.models.detector_context import DetectorContext, TelemetryPoint
from issues.models.issue_candidate import IssueCandidate, IssueIdentity

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _TiltSample:
    timestamp: datetime.datetime
    actual_degrees: float
    ideal_degrees: float
    difference_degrees: float
    is_out_of_position: bool


class PoaSensorOutOfPositionDetector:
    """Emit candidates when POA tilt sensors diverge from ideal tracking."""

    def __init__(
        self,
        *,
        issue_category_id: int,
        config: PoaSensorOutOfPositionConfig,
    ) -> None:
        self.name = config.detector_name
        self._config = config
        self._issue_category_id = issue_category_id

    def detect(
        self,
        *,
        context: DetectorContext,
    ) -> list[IssueCandidate]:
        """Detect POA tilt channels that are out of tracker position."""
        candidates: list[IssueCandidate] = []
        window_start = context.run_time - datetime.timedelta(
            minutes=self._config.evaluation_window_minutes
        )
        LOGGER.info(
            "Analyzing POA tilt position window start=%s end=%s",
            window_start.isoformat(),
            context.run_time.isoformat(),
        )
        for channel in context.met_station_channels:
            if channel.sensor_type_id != SensorTypeEnum.MET_STATION_POA_TILT.value:
                continue
            if channel.latitude is None or channel.longitude is None:
                LOGGER.info(
                    "Skipping POA tilt channel with unresolved coordinates "
                    "device_id=%s tag_id=%s",
                    channel.device_id,
                    channel.tag_id,
                )
                continue
            samples = self._build_tilt_samples(
                points=context.get_channel_points(
                    device_id=channel.device_id,
                    tag_id=channel.tag_id,
                ),
                window_start=window_start,
                run_time=context.run_time,
                latitude=channel.latitude,
                longitude=channel.longitude,
            )
            if not samples:
                continue
            out_of_position = [
                sample for sample in samples if sample.is_out_of_position
            ]
            motion_mismatch = self._has_motion_mismatch(samples=samples)
            if (
                len(out_of_position) < self._config.minimum_samples_to_open
                and not motion_mismatch
            ):
                continue
            first_bad_time = (
                out_of_position[0].timestamp
                if out_of_position
                else samples[0].timestamp
            )
            last_bad_time = (
                out_of_position[-1].timestamp
                if out_of_position
                else samples[-1].timestamp
            )
            time_end = (
                last_bad_time
                if self._has_recovery_after_last_bad(
                    samples=samples,
                    last_bad_time=last_bad_time,
                )
                else None
            )
            metadata = self._build_metadata(
                samples=samples,
                out_of_position_samples=out_of_position,
                motion_mismatch=motion_mismatch,
                time_end=time_end,
            )
            candidates.append(
                IssueCandidate(
                    project_id=context.project_id,
                    detector_name=self.name,
                    identity=IssueIdentity(
                        device_id=channel.device_id,
                        tag_id=channel.tag_id,
                        issue_category_id=self._issue_category_id,
                    ),
                    time_start=first_bad_time,
                    time_end=time_end,
                    detector_metadata=metadata,
                )
            )
        return candidates

    def _build_tilt_samples(
        self,
        *,
        points: tuple[TelemetryPoint, ...],
        window_start: datetime.datetime,
        run_time: datetime.datetime,
        latitude: float,
        longitude: float,
    ) -> tuple[_TiltSample, ...]:
        candidate_points = tuple(
            point for point in points if window_start <= point.time <= run_time
        )
        timestamps = tuple(point.time for point in candidate_points)
        if not timestamps:
            return ()
        ideal_by_time = self._ideal_tracking_curve_by_time(
            timestamps=timestamps,
            latitude=latitude,
            longitude=longitude,
        )
        samples: list[_TiltSample] = []
        for point in candidate_points:
            actual = _parse_finite_degrees(value=point.value)
            ideal = ideal_by_time.get(point.time)
            if actual is None or ideal is None:
                continue
            difference = abs(actual - ideal)
            samples.append(
                _TiltSample(
                    timestamp=point.time,
                    actual_degrees=actual,
                    ideal_degrees=ideal,
                    difference_degrees=difference,
                    is_out_of_position=(
                        difference > self._config.angle_tolerance_degrees
                    ),
                )
            )
        return tuple(sorted(samples, key=lambda sample: sample.timestamp))

    def _ideal_tracking_curve_by_time(
        self,
        *,
        timestamps: tuple[datetime.datetime, ...],
        latitude: float,
        longitude: float,
    ) -> dict[datetime.datetime, float | None]:
        normalized = _normalize_timestamps(timestamps=timestamps)
        time_index = pd.DatetimeIndex(normalized)
        if time_index.tz is None:
            msg = "PVLib tracker evaluation requires timezone-aware timestamps"
            raise ValueError(msg)
        solar = solarposition.get_solarposition(
            time=time_index,
            latitude=latitude,
            longitude=longitude,
        )
        is_daylight = (
            solar["apparent_elevation"]
            > self._config.daylight_apparent_elevation_threshold_degrees
        )
        tracker_curve = tracking.singleaxis(
            apparent_zenith=solar["apparent_zenith"],
            solar_azimuth=solar["azimuth"],
            axis_tilt=self._config.tracker_axis_tilt_degrees,
            axis_azimuth=self._config.tracker_axis_azimuth_degrees,
            max_angle=self._config.tracker_max_angle_degrees,
            backtrack=self._config.tracker_backtrack,
            gcr=self._config.tracker_ground_coverage_ratio,
        )
        ideal_by_time: dict[datetime.datetime, float | None] = {}
        for timestamp, daylight, tracker_theta in zip(
            timestamps,
            is_daylight,
            tracker_curve["tracker_theta"],
            strict=True,
        ):
            if not bool(daylight) or not math.isfinite(float(tracker_theta)):
                ideal_by_time[timestamp] = None
                continue
            ideal_by_time[timestamp] = abs(float(tracker_theta))
        return ideal_by_time

    def _has_motion_mismatch(self, *, samples: tuple[_TiltSample, ...]) -> bool:
        if len(samples) < self._config.minimum_samples_to_open:
            return False
        ideal_movement = _angle_range(
            values=tuple(sample.ideal_degrees for sample in samples)
        )
        actual_movement = _angle_range(
            values=tuple(sample.actual_degrees for sample in samples)
        )
        return (
            ideal_movement >= self._config.minimum_ideal_movement_degrees
            and actual_movement < self._config.minimum_actual_movement_degrees
        )

    def _has_recovery_after_last_bad(
        self,
        *,
        samples: tuple[_TiltSample, ...],
        last_bad_time: datetime.datetime,
    ) -> bool:
        recovery_samples = tuple(
            sample
            for sample in samples
            if sample.timestamp > last_bad_time and not sample.is_out_of_position
        )
        if len(recovery_samples) < self._config.minimum_recovery_samples_to_close:
            return False
        ideal_movement = _angle_range(
            values=tuple(sample.ideal_degrees for sample in recovery_samples)
        )
        actual_movement = _angle_range(
            values=tuple(sample.actual_degrees for sample in recovery_samples)
        )
        return (
            ideal_movement >= self._config.minimum_ideal_movement_degrees
            and actual_movement >= self._config.minimum_actual_movement_degrees
        )

    def _build_metadata(
        self,
        *,
        samples: tuple[_TiltSample, ...],
        out_of_position_samples: list[_TiltSample],
        motion_mismatch: bool,
        time_end: datetime.datetime | None,
    ) -> dict[str, object]:
        max_difference = max(
            (sample.difference_degrees for sample in samples),
            default=0.0,
        )
        return {
            "detector_name": self.name,
            "evaluation_window_minutes": self._config.evaluation_window_minutes,
            "angle_tolerance_degrees": self._config.angle_tolerance_degrees,
            "sample_count": len(samples),
            "out_of_position_samples": len(out_of_position_samples),
            "max_difference_degrees": round(max_difference, 4),
            "motion_mismatch_detected": motion_mismatch,
            "should_close": time_end is not None,
            "latest_sample_time": samples[-1].timestamp.isoformat(),
            "candidate_time_end": time_end.isoformat() if time_end else None,
        }


def _normalize_timestamps(
    *,
    timestamps: tuple[datetime.datetime, ...],
) -> tuple[datetime.datetime, ...]:
    return tuple(
        timestamp.replace(tzinfo=datetime.UTC)
        if timestamp.tzinfo is None
        else timestamp
        for timestamp in timestamps
    )


def _parse_finite_degrees(*, value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        return None
    if not parsed.is_finite():
        return None
    return float(parsed)


def _angle_range(*, values: tuple[float, ...]) -> float:
    if not values:
        return 0.0
    return max(values) - min(values)
