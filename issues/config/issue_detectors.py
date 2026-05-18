"""Static config used by detector modules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MetStationNonCommunicatingConfig:
    """Config for the met station non-communicating detector."""

    detector_name: str = "met_station_non_communicating"
    issue_category_name: str = "Met Station Non-Communicating"
    evaluation_window_minutes: int = 120
    expected_interval_minutes_default: int = 5
    minimum_missing_samples_to_open: int = 3
    open_missing_ratio_threshold: float = 0.85
    daylight_apparent_elevation_threshold_degrees: float = 10.0


@dataclass(frozen=True)
class PoaSensorOutOfPositionConfig:
    """Config for the POA sensor out-of-position detector."""

    detector_name: str = "poa_sensor_out_of_position"
    issue_category_name: str = "POA Sensor Out of Position"
    evaluation_window_minutes: int = 120
    expected_interval_minutes_default: int = 5
    angle_tolerance_degrees: float = 5.0
    minimum_samples_to_open: int = 3
    daylight_apparent_elevation_threshold_degrees: float = 10.0
    tracker_axis_tilt_degrees: float = 0.0
    tracker_axis_azimuth_degrees: float = 0.0
    tracker_max_angle_degrees: float = 90.0
    tracker_backtrack: bool = True
    tracker_ground_coverage_ratio: float = 2.0 / 7.0
    minimum_recovery_samples_to_close: int = 3
    minimum_ideal_movement_degrees: float = 5.0
    minimum_actual_movement_degrees: float = 2.0


@dataclass(frozen=True)
class IssueDetectorConfig:
    """Top-level config for all issue detectors."""

    met_station_non_communicating: MetStationNonCommunicatingConfig
    poa_sensor_out_of_position: PoaSensorOutOfPositionConfig


def get_default_issue_detector_config() -> IssueDetectorConfig:
    """Return default issue-detector settings."""
    return IssueDetectorConfig(
        met_station_non_communicating=MetStationNonCommunicatingConfig(),
        poa_sensor_out_of_position=PoaSensorOutOfPositionConfig(),
    )
