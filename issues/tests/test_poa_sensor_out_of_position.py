import datetime

import pandas as pd
from core.enumerations import SensorTypeEnum

from issues.config.issue_detectors import PoaSensorOutOfPositionConfig
from issues.detectors import poa_sensor_out_of_position as detector_module
from issues.detectors.poa_sensor_out_of_position import (
    PoaSensorOutOfPositionDetector,
)
from issues.models.detector_context import (
    DetectorContext,
    MetStationChannel,
    TelemetryPoint,
)


def _build_poa_context(
    *,
    points: tuple[TelemetryPoint, ...],
    sensor_type_id: int | None = SensorTypeEnum.MET_STATION_POA_TILT.value,
) -> DetectorContext:
    run_time = datetime.datetime(2026, 6, 1, 12, 30, tzinfo=datetime.UTC)
    channel = MetStationChannel(
        device_id=1,
        tag_id=2,
        sensor_type_id=sensor_type_id,
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


def _build_points(
    *,
    start: datetime.datetime,
    values: tuple[float, ...],
) -> tuple[TelemetryPoint, ...]:
    return tuple(
        TelemetryPoint(
            device_id=1,
            tag_id=2,
            time=start + datetime.timedelta(minutes=index * 5),
            value=str(value),
        )
        for index, value in enumerate(values)
    )


def test_detector_opens_at_first_bad_and_closes_at_last_bad(
    *,
    monkeypatch,
) -> None:
    """Candidate bounds use first and last out-of-position samples."""
    detector = PoaSensorOutOfPositionDetector(
        issue_category_id=12,
        config=PoaSensorOutOfPositionConfig(),
    )
    start = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)
    points = _build_points(start=start, values=(0, 0, 0, 25, 30, 35))
    ideal_values = (10, 15, 20, 25, 30, 35)
    monkeypatch.setattr(
        detector,
        "_ideal_tracking_curve_by_time",
        lambda *, timestamps, latitude, longitude: dict(
            zip(timestamps, ideal_values, strict=True)
        ),
    )

    candidates = detector.detect(context=_build_poa_context(points=points))

    assert len(candidates) == 1
    assert candidates[0].time_start == start
    assert candidates[0].time_end == start + datetime.timedelta(minutes=10)
    assert candidates[0].detector_metadata["out_of_position_samples"] == 3


def test_detector_keeps_stuck_sensor_open_at_broken_clock_crossing(
    *,
    monkeypatch,
) -> None:
    """Stuck sensors remain open even when briefly near the ideal curve."""
    detector = PoaSensorOutOfPositionDetector(
        issue_category_id=12,
        config=PoaSensorOutOfPositionConfig(),
    )
    start = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)
    points = _build_points(start=start, values=(0, 0, 0, 0, 0, 0))
    ideal_values = (20, 15, 10, 5, 0, 5)
    monkeypatch.setattr(
        detector,
        "_ideal_tracking_curve_by_time",
        lambda *, timestamps, latitude, longitude: dict(
            zip(timestamps, ideal_values, strict=True)
        ),
    )

    candidates = detector.detect(context=_build_poa_context(points=points))

    assert len(candidates) == 1
    assert candidates[0].time_start == start
    assert candidates[0].time_end is None
    assert candidates[0].detector_metadata["motion_mismatch_detected"] is True


def test_detector_ignores_non_poa_tilt_channels(*, monkeypatch) -> None:
    """Only MET_STATION_POA_TILT channels are evaluated."""
    detector = PoaSensorOutOfPositionDetector(
        issue_category_id=12,
        config=PoaSensorOutOfPositionConfig(),
    )
    start = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)
    points = _build_points(start=start, values=(0, 0, 0, 0))
    monkeypatch.setattr(
        detector,
        "_ideal_tracking_curve_by_time",
        lambda *, timestamps, latitude, longitude: {
            timestamp: 20 for timestamp in timestamps
        },
    )

    candidates = detector.detect(
        context=_build_poa_context(
            points=points,
            sensor_type_id=SensorTypeEnum.MET_STATION_POA.value,
        )
    )

    assert candidates == []


def test_ideal_tracking_curve_uses_absolute_tracker_angle(
    *,
    monkeypatch,
) -> None:
    """Ideal tracker angles are absolute because POA tilt telemetry is positive."""
    detector = PoaSensorOutOfPositionDetector(
        issue_category_id=12,
        config=PoaSensorOutOfPositionConfig(),
    )
    timestamp = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)
    monkeypatch.setattr(
        detector_module.solarposition,
        "get_solarposition",
        lambda *, time, latitude, longitude: pd.DataFrame(
            {
                "apparent_elevation": [45.0],
                "apparent_zenith": [45.0],
                "azimuth": [180.0],
            },
            index=time,
        ),
    )
    monkeypatch.setattr(
        detector_module.tracking,
        "singleaxis",
        lambda **_: pd.DataFrame({"tracker_theta": [-12.5]}),
    )

    ideal_by_time = detector._ideal_tracking_curve_by_time(
        timestamps=(timestamp,),
        latitude=35.0,
        longitude=-97.0,
    )

    assert ideal_by_time[timestamp] == 12.5
