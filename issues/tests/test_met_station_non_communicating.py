import datetime

from issues.config.issue_detectors import MetStationNonCommunicatingConfig
from issues.detectors.met_station_non_communicating import (
    MetStationNonCommunicatingDetector,
)
from issues.models.detector_context import DetectorContext, MetStationChannel, TelemetryPoint


def _build_context(*, points: tuple[TelemetryPoint, ...]) -> DetectorContext:
    run_time = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)
    channel = MetStationChannel(
        device_id=1,
        tag_id=2,
        expected_interval_minutes=5,
        latitude=35.0,
        longitude=-97.0,
    )
    return DetectorContext(
        project_id="project-1",
        run_time=run_time,
        project_latitude=35.0,
        project_longitude=-97.0,
        met_station_channels=(channel,),
        telemetry_by_channel={(1, 2): points},
    )


def test_detector_daylight_window_keeps_current_behavior(*, monkeypatch) -> None:
    detector = MetStationNonCommunicatingDetector(
        issue_category_id=11,
        config=MetStationNonCommunicatingConfig(),
    )
    run_time = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)
    points = tuple(
        TelemetryPoint(
            device_id=1,
            tag_id=2,
            time=run_time - datetime.timedelta(minutes=offset * 5),
            value=None,
        )
        for offset in range(24)
    )
    context = _build_context(points=points)
    monkeypatch.setattr(
        detector,
        "_is_daytime_timestamps",
        lambda *, timestamps, latitude, longitude: tuple(True for _ in timestamps),
    )

    candidates = detector.detect(context=context)

    assert len(candidates) == 1
    assert candidates[0].detector_metadata["expected_samples"] == 24
    assert candidates[0].detector_metadata["present_samples"] == 0


def test_detector_nighttime_window_emits_no_candidate(*, monkeypatch) -> None:
    detector = MetStationNonCommunicatingDetector(
        issue_category_id=11,
        config=MetStationNonCommunicatingConfig(),
    )
    run_time = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)
    points = tuple(
        TelemetryPoint(
            device_id=1,
            tag_id=2,
            time=run_time - datetime.timedelta(minutes=offset * 5),
            value=None,
        )
        for offset in range(24)
    )
    context = _build_context(points=points)
    monkeypatch.setattr(
        detector,
        "_is_daytime_timestamps",
        lambda *, timestamps, latitude, longitude: tuple(False for _ in timestamps),
    )

    assert detector.detect(context=context) == []


def test_detector_mixed_window_uses_daylight_only(*, monkeypatch) -> None:
    detector = MetStationNonCommunicatingDetector(
        issue_category_id=11,
        config=MetStationNonCommunicatingConfig(),
    )
    run_time = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)
    points = tuple(
        TelemetryPoint(
            device_id=1,
            tag_id=2,
            time=run_time - datetime.timedelta(minutes=offset * 5),
            value=None,
        )
        for offset in range(24)
    )
    context = _build_context(points=points)

    def mixed_daytime(*, timestamps, latitude, longitude):
        return tuple(index < 12 for index, _ in enumerate(timestamps))

    monkeypatch.setattr(detector, "_is_daytime_timestamps", mixed_daytime)

    candidates = detector.detect(context=context)

    assert len(candidates) == 1
    assert candidates[0].detector_metadata["expected_samples"] == 12
    assert candidates[0].detector_metadata["missing_samples"] == 12


def test_daytime_helper_normalizes_naive_timestamps_to_aware() -> None:
    detector = MetStationNonCommunicatingDetector(
        issue_category_id=11,
        config=MetStationNonCommunicatingConfig(),
    )
    timestamps = (
        datetime.datetime(2026, 6, 1, 12, 0),
        datetime.datetime(2026, 6, 1, 12, 5),
    )
    result = detector._is_daytime_timestamps(
        timestamps=timestamps,
        latitude=35.0,
        longitude=-97.0,
    )
    assert len(result) == 2
