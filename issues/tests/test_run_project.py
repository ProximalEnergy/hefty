import logging
from typing import cast

from issues.config.issue_detectors import get_default_issue_detector_config
from issues.orchestrator.run_project import _build_configured_detectors
from issues.persistence.repository import IssueRepository


class _FakeRepository:
    def get_issue_category_id(self, *, category_name: str) -> int:
        category_ids = {
            "Met Station Non-Communicating": 101,
            "POA Sensor Out of Position": 102,
        }
        return category_ids[category_name]


def test_build_configured_detectors_defaults_to_all() -> None:
    """All configured detectors are enabled when no category filter is passed."""
    configured = _build_configured_detectors(
        detector_config=get_default_issue_detector_config(),
        repository=cast(IssueRepository, _FakeRepository()),
        issue_category_ids=None,
    )
    assert len(configured) == 2
    assert configured[0].issue_category_id == 101
    assert configured[0].requirements.telemetry_window_minutes == 120
    assert configured[1].issue_category_id == 102


def test_build_configured_detectors_filters_supported_subset() -> None:
    """Supported category filters include only matching detectors."""
    configured = _build_configured_detectors(
        detector_config=get_default_issue_detector_config(),
        repository=cast(IssueRepository, _FakeRepository()),
        issue_category_ids=[102],
    )
    assert len(configured) == 1
    assert configured[0].issue_category_id == 102


def test_build_configured_detectors_skips_unsupported_with_warning(
    *,
    caplog,
) -> None:
    """Unsupported category filters are skipped with a warning."""
    with caplog.at_level(logging.WARNING):
        configured = _build_configured_detectors(
            detector_config=get_default_issue_detector_config(),
            repository=cast(IssueRepository, _FakeRepository()),
            issue_category_ids=[999],
        )
    assert configured == []
    assert "Skipping unsupported issue_category_ids=[999]" in caplog.text
