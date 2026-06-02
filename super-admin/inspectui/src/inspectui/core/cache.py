"""Load and save per-project device/tag snapshots as JSON.

Files live under ``~/.inspectui/cache/``.
"""

import json
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import UUID

from inspectui.core.models import (
    DeviceInfo,
    ProjectInfo,
    TagInfo,
    TestResult,
    TestRunSummary,
    TestStatus,
)


def _test_result_to_jsonable(*, result: TestResult) -> dict[str, object]:
    """Serialize a test result for JSON storage."""
    return {
        "test_name": result.test_name,
        "passed": result.passed,
        "message": result.message,
        "status": int(result.status),
        "details": result.details,
        "project_name": result.project_name,
        "params": result.params,
    }


def _human_readable_age_from_mtime(*, cache_path: Path) -> str | None:
    """Format cache age from file mtime (no JSON parse; safe for huge files)."""
    try:
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
    except OSError:
        return None
    age = datetime.now() - mtime
    if age.days > 0:
        return f"{age.days}d ago"
    if age.seconds >= 3600:
        return f"{age.seconds // 3600}h ago"
    if age.seconds >= 60:
        return f"{age.seconds // 60}m ago"
    return "just now"


def _test_result_from_dict(*, data: dict[str, object]) -> TestResult:
    """Deserialize a test result from JSON-compatible dict."""
    details = data.get("details")
    if details is not None and not isinstance(details, dict):
        details = None
    params = data.get("params")
    if params is not None and not isinstance(params, dict):
        params = None
    project_name = data.get("project_name")
    return TestResult(
        test_name=str(data["test_name"]),
        passed=bool(data.get("passed", False)),
        message=str(data.get("message", "")),
        status=TestStatus(int(data.get("status", 0))),
        details=details,
        project_name=str(project_name) if project_name else None,
        params=params,
    )


class CacheManager:
    """Manages in-memory and file-based cache of project data."""

    DEFAULT_CACHE_DIR = Path.home() / ".inspectui" / "cache"
    CACHE_TTL_HOURS = None  # None = indefinite (no expiration)

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or self.DEFAULT_CACHE_DIR
        self.current_project: ProjectInfo | None = None
        self.devices: list[DeviceInfo] = []
        self.tags: list[TagInfo] = []

        # Lookup dictionaries for fast access
        self._device_by_id: dict[int, DeviceInfo] = {}
        self._devices_by_type: dict[int, list[DeviceInfo]] = {}
        self._tags_by_device: dict[int, list[TagInfo]] = {}

    def set_project(
        self,
        project: ProjectInfo,
        devices: list[DeviceInfo],
        tags: list[TagInfo],
        save_to_disk: bool = True,
    ) -> None:
        """Set the current project and its data.

        Args:
            project: The project info.
            devices: List of devices for the project.
            tags: List of tags for the project.
            save_to_disk: Whether to persist cache to disk.
        """
        self.current_project = project
        self.devices = devices
        self.tags = tags
        self._build_lookups()

        if save_to_disk:
            self.save_to_disk()

    def _build_lookups(self) -> None:
        """Build lookup dictionaries for fast access."""
        self._device_by_id = {d.device_id: d for d in self.devices}

        devices_by_type: defaultdict[int, list[DeviceInfo]] = defaultdict(list)
        for device in self.devices:
            devices_by_type[device.device_type_id].append(device)
        self._devices_by_type = devices_by_type

        tags_by_device: defaultdict[int, list[TagInfo]] = defaultdict(list)
        for tag in self.tags:
            tags_by_device[tag.device_id].append(tag)
        self._tags_by_device = tags_by_device

    def clear(self) -> None:
        """Clear all cached data from memory."""
        self.current_project = None
        self.devices = []
        self.tags = []
        self._device_by_id = {}
        self._devices_by_type = {}
        self._tags_by_device = {}

    def get_device(self, device_id: int) -> DeviceInfo | None:
        """Get a device by ID."""
        return self._device_by_id.get(device_id)

    def get_devices_by_type(self, device_type_id: int) -> list[DeviceInfo]:
        """Get all devices of a specific type."""
        return self._devices_by_type.get(device_type_id, [])

    def get_tags_for_device(self, device_id: int) -> list[TagInfo]:
        """Get all tags for a specific device."""
        return self._tags_by_device.get(device_id, [])

    def get_device_type_counts(self) -> dict[int, int]:
        """Get count of devices per device type."""
        return {k: len(v) for k, v in self._devices_by_type.items()}

    # --- File-based caching ---

    def _get_cache_path(self, project_name: str) -> Path:
        """Get the cache file path for a project."""
        return self.cache_dir / f"{project_name}.json"

    def _get_projects_cache_path(self) -> Path:
        """Get the cache file path for the project list."""
        return self.cache_dir / "projects.json"

    def has_projects_cache(self) -> bool:
        """Check if project list cache exists."""
        return self._get_projects_cache_path().exists()

    def get_projects_cache_age(self) -> str | None:
        """Get human-readable cache age for the project list."""
        cache_path = self._get_projects_cache_path()
        if not cache_path.exists():
            return None
        return _human_readable_age_from_mtime(cache_path=cache_path)

    def load_projects_from_disk(self) -> list[ProjectInfo] | None:
        """Load cached project list from disk."""
        cache_path = self._get_projects_cache_path()
        if not cache_path.exists():
            return None

        try:
            with open(cache_path) as f:
                data = json.load(f)

            projects = []
            for proj_data in data.get("projects", []):
                if proj_data.get("cod"):
                    proj_data["cod"] = date.fromisoformat(proj_data["cod"])
                proj_data["project_id"] = UUID(proj_data["project_id"])
                projects.append(ProjectInfo(**proj_data))
            return projects
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None

    def save_projects_to_disk(self, *, projects: list[ProjectInfo]) -> bool:
        """Save project list to disk."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = self._get_projects_cache_path()

            data = {
                "cached_at": datetime.now().isoformat(),
                "projects": [],
            }

            for project in projects:
                proj_dict = asdict(project)
                proj_dict["project_id"] = str(proj_dict["project_id"])
                if proj_dict.get("cod"):
                    proj_dict["cod"] = proj_dict["cod"].isoformat()
                data["projects"].append(proj_dict)

            with open(cache_path, "w") as f:
                json.dump(data, f)

            return True
        except (OSError, TypeError):
            return False

    def has_valid_cache(self, project_name: str) -> bool:
        """Check if valid cache exists for a project.

        Args:
            project_name: The project's short name.

        Returns:
            True if cache exists and is not expired.
        """
        cache_path = self._get_cache_path(project_name)
        if not cache_path.exists():
            return False

        # If TTL is None, cache never expires
        if self.CACHE_TTL_HOURS is None:
            return True

        try:
            with open(cache_path) as f:
                data = json.load(f)

            cached_at = datetime.fromisoformat(data.get("cached_at", ""))
            ttl = timedelta(hours=self.CACHE_TTL_HOURS)
            return datetime.now() - cached_at < ttl
        except (json.JSONDecodeError, ValueError, KeyError):
            return False

    def get_cache_age(self, project_name: str) -> str | None:
        """Get human-readable cache age for a project.

        Uses file mtime only (does not parse JSON) so listing many projects
        stays fast even when cache files are large.

        Args:
            project_name: The project's short name.

        Returns:
            Human-readable age string or None if no cache.
        """
        cache_path = self._get_cache_path(project_name)
        if not cache_path.exists():
            return None
        return _human_readable_age_from_mtime(cache_path=cache_path)

    def load_from_disk(self, project_name: str) -> bool:
        """Load cached data for a project from disk.

        Args:
            project_name: The project's short name.

        Returns:
            True if cache was loaded successfully.
        """
        cache_path = self._get_cache_path(project_name)
        if not cache_path.exists():
            return False

        try:
            with open(cache_path) as f:
                data = json.load(f)

            # Reconstruct ProjectInfo
            proj_data = data["project"]
            # Handle date field
            if proj_data.get("cod"):
                proj_data["cod"] = date.fromisoformat(proj_data["cod"])
            # Handle UUID field
            proj_data["project_id"] = UUID(proj_data["project_id"])

            self.current_project = ProjectInfo(**proj_data)

            # Reconstruct devices
            self.devices = [DeviceInfo(**d) for d in data["devices"]]

            # Reconstruct tags
            self.tags = [TagInfo(**t) for t in data["tags"]]

            self._build_lookups()
            return True

        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return False

    def save_to_disk(self) -> bool:
        """Save current project data to disk.

        Returns:
            True if saved successfully.
        """
        if not self.current_project:
            return False

        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path = self._get_cache_path(self.current_project.name_short)

            # Convert to JSON-serializable format
            proj_dict = asdict(self.current_project)
            proj_dict["project_id"] = str(proj_dict["project_id"])
            if proj_dict.get("cod"):
                proj_dict["cod"] = proj_dict["cod"].isoformat()

            data = {
                "cached_at": datetime.now().isoformat(),
                "project": proj_dict,
                "devices": [asdict(d) for d in self.devices],
                "tags": [asdict(t) for t in self.tags],
            }

            with open(cache_path, "w") as f:
                json.dump(data, f)

            return True

        except (OSError, TypeError):
            return False

    def invalidate_cache(self, project_name: str) -> bool:
        """Delete cached data for a project.

        Args:
            project_name: The project's short name.

        Returns:
            True if cache was deleted.
        """
        cache_path = self._get_cache_path(project_name)
        if cache_path.exists():
            cache_path.unlink()
            return True
        return False

    def clear_projects_list_cache(self) -> bool:
        """Delete cached operational.projects list (``projects.json``).

        Returns:
            True if a file was removed.
        """
        cache_path = self._get_projects_cache_path()
        if not cache_path.exists():
            return False
        cache_path.unlink()
        return True

    def prune_project_payload_caches(self, *, keep_names: set[str]) -> int:
        """Delete per-project device/tag JSON not in ``keep_names``.

        Args:
            keep_names: ``name_short`` values to retain on disk.

        Returns:
            Number of cache files deleted.
        """
        if not self.cache_dir.exists():
            return 0

        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.name in ("projects.json", "last_test_run.json"):
                continue
            if cache_file.stem not in keep_names:
                cache_file.unlink()
                count += 1
        return count

    def invalidate_all_cache(self) -> int:
        """Delete all cached project data.

        Returns:
            Number of cache files deleted.
        """
        if not self.cache_dir.exists():
            return 0

        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        return count

    def _get_last_test_run_path(self) -> Path:
        """Path to persisted last test run summary."""
        return self.cache_dir / "last_test_run.json"

    def save_last_test_run(self, *, summary: TestRunSummary) -> bool:
        """Persist the last test run for review from the main menu.

        Args:
            summary: Aggregated results to save.

        Returns:
            True if the file was written.
        """
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._get_last_test_run_path()
            recorded = summary.recorded_at or datetime.now()
            payload = {
                "recorded_at": recorded.isoformat(),
                "total": summary.total,
                "passed": summary.passed,
                "failed": summary.failed,
                "skipped": summary.skipped,
                "errors": summary.errors,
                "results": [
                    _test_result_to_jsonable(result=r) for r in summary.results
                ],
            }
            with open(path, "w") as f:
                json.dump(payload, f)
            return True
        except (OSError, TypeError, ValueError):
            return False

    def load_last_test_run(self) -> TestRunSummary | None:
        """Load the last persisted test run, if any."""
        path = self._get_last_test_run_path()
        if not path.exists():
            return None
        try:
            with open(path) as f:
                payload = json.load(f)
            raw_recorded = payload.get("recorded_at")
            recorded_at = datetime.fromisoformat(raw_recorded) if raw_recorded else None
            raw_results = payload.get("results", [])
            results: list[TestResult] = []
            for item in raw_results:
                if not isinstance(item, dict):
                    return None
                results.append(
                    _test_result_from_dict(data=dict(item)),
                )
            return TestRunSummary(
                total=int(payload["total"]),
                passed=int(payload["passed"]),
                failed=int(payload["failed"]),
                skipped=int(payload["skipped"]),
                errors=int(payload["errors"]),
                results=results,
                recorded_at=recorded_at,
            )
        except (OSError, TypeError, ValueError, KeyError):
            return None
