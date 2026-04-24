"""Detector for met station non-communication conditions."""

import datetime
import math

from issues.config.issue_detectors import MetStationNonCommunicatingConfig
from issues.models.detector_context import DetectorContext, TelemetryPoint
from issues.models.issue_candidate import IssueCandidate, IssueIdentity


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
        for channel in context.met_station_channels:
            expected = self._expected_samples(
                expected_interval_minutes=channel.expected_interval_minutes
            )
            points = context.get_channel_points(
                device_id=channel.device_id,
                tag_id=channel.tag_id,
            )
            present_count, latest_point = self._present_samples(
                points=points,
                window_start=window_start,
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

    def _expected_samples(
        self,
        *,
        expected_interval_minutes: int,
    ) -> int:
        window = self._config.evaluation_window_minutes
        interval = max(1, expected_interval_minutes)
        return max(1, math.ceil(window / interval))

    def _present_samples(
        self,
        *,
        points: tuple[TelemetryPoint, ...],
        window_start: datetime.datetime,
    ) -> tuple[int, datetime.datetime | None]:
        present_count = 0
        latest_point: datetime.datetime | None = None
        for point in points:
            if point.time < window_start:
                continue
            if latest_point is None or point.time > latest_point:
                latest_point = point.time
            if point.value is None or point.value == "":
                continue
            present_count += 1
        return present_count, latest_point
