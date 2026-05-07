"""Static config used by detector modules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MetStationNonCommunicatingConfig:
    """Config for the met station non-communicating detector."""

    detector_name: str = "met_station_non_communicating"
    issue_category_name: str = "Met Station Non-Communicating"
    evaluation_window_minutes: int = 60
    expected_interval_minutes_default: int = 5
    minimum_missing_samples_to_open: int = 3
    open_missing_ratio_threshold: float = 0.85
    daylight_apparent_elevation_threshold_degrees: float = 10.0


@dataclass(frozen=True)
class IssueDetectorConfig:
    """Top-level config for all issue detectors."""

    met_station_non_communicating: MetStationNonCommunicatingConfig


def get_default_issue_detector_config() -> IssueDetectorConfig:
    """Return default issue-detector settings."""
    return IssueDetectorConfig(
        met_station_non_communicating=MetStationNonCommunicatingConfig(),
    )
