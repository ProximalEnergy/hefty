"""Plain dataclasses for project/device/tag rows and test outcomes.

Fields align with ``DataFetcher`` / ``csv_loader`` and per-project schemas.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum
from typing import Any
from uuid import UUID


class TestStatus(IntEnum):
    """Test result status."""

    PASSED = 0
    FAILED = 1
    SKIPPED = 2
    ERROR = 3


@dataclass
class ProjectInfo:
    """Project information from operational.projects."""

    project_id: UUID
    project_id_int: int
    name_short: str
    name_long: str
    data_table: str
    project_type_id: int
    project_status_type_id: int
    capacity_dc: float
    capacity_ac: float
    cod: date | None
    time_zone: str

    @property
    def display_name(self) -> str:
        """Return a display-friendly name."""
        return f"{self.name_short} ({self.name_long})"


@dataclass
class DeviceInfo:
    """Device information from {project}.devices."""

    device_id: int
    device_type_id: int
    name_short: str | None
    name_long: str | None
    parent_device_id: int | None
    capacity_dc: float | None
    capacity_ac: float | None
    capacity_energy_dc: float | None = None
    device_model_id: int | None = None

    @property
    def display_name(self) -> str:
        """Return a display-friendly name."""
        return self.name_short or self.name_long or f"Device {self.device_id}"


@dataclass
class TagInfo:
    """Tag information from {project}.tags."""

    tag_id: int
    device_id: int
    sensor_type_id: int | None
    data_type_id: int | None
    name_short: str | None
    name_long: str | None
    name_scada: str
    in_tsdb: bool

    @property
    def display_name(self) -> str:
        """Return a display-friendly name."""
        return self.name_short or self.name_long or self.name_scada


@dataclass
class TestResult:
    """Result of a single test execution."""

    test_name: str
    passed: bool
    message: str
    status: TestStatus = TestStatus.PASSED
    details: dict[str, Any] | None = None
    project_name: str | None = None
    params: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status == TestStatus.PASSED:
            self.status = TestStatus.PASSED if self.passed else TestStatus.FAILED


@dataclass
class TestRunSummary:
    """Summary of a test run across multiple tests."""

    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    results: list[TestResult]
    recorded_at: datetime | None = None

    @property
    def all_passed(self) -> bool:
        """Return True if all tests passed."""
        return self.failed == 0 and self.errors == 0

    @property
    def failing_project_names(self) -> list[str]:
        """Project name_shorts with at least one failed or errored test."""
        names: set[str] = set()
        for result in self.results:
            if result.project_name is None:
                continue
            if result.status in (TestStatus.FAILED, TestStatus.ERROR):
                names.add(result.project_name)
        return sorted(names)
