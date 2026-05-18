"""Context payload passed into issue detectors."""

import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class MetStationChannel:
    """Monitored met-station channel config row."""

    device_id: int
    tag_id: int | None
    sensor_type_id: int | None
    expected_interval_minutes: int
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True)
class TelemetryPoint:
    """Single telemetry row for a met-station channel."""

    device_id: int
    tag_id: int | None
    time: datetime.datetime
    value: str | None


@dataclass(frozen=True)
class DetectorContext:
    """Normalized detector context for one project and run timestamp."""

    project_id: str
    run_time: datetime.datetime
    project_latitude: float | None
    project_longitude: float | None
    met_station_channels: tuple[MetStationChannel, ...]
    telemetry_by_channel: dict[tuple[int, int | None], tuple[TelemetryPoint, ...]]

    def get_channel_points(
        self,
        *,
        device_id: int,
        tag_id: int | None,
    ) -> tuple[TelemetryPoint, ...]:
        """Return telemetry points for a channel key."""
        return self.telemetry_by_channel.get((device_id, tag_id), ())
