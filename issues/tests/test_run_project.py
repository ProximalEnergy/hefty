import logging
from typing import cast

from issues.config.issue_detectors import get_default_issue_detector_config
from issues.orchestrator.run_project import _build_configured_detectors
from issues.persistence.repository import IssueRepository


class _FakeRepository:
    def get_issue_category_id(self, *, category_name: str) -> int:
        assert category_name == "Met Station Non-Communicating"
        return 101


def test_build_configured_detectors_defaults_to_all() -> None:
    configured = _build_configured_detectors(
        detector_config=get_default_issue_detector_config(),
            repository=cast(IssueRepository, _FakeRepository()),
        issue_category_ids=None,
    )
    assert len(configured) == 1
    assert configured[0].issue_category_id == 101
    assert configured[0].requirements.telemetry_window_minutes == 120


def test_build_configured_detectors_filters_supported_subset() -> None:
    configured = _build_configured_detectors(
        detector_config=get_default_issue_detector_config(),
            repository=cast(IssueRepository, _FakeRepository()),
        issue_category_ids=[101],
    )
    assert len(configured) == 1


def test_build_configured_detectors_skips_unsupported_with_warning(
    *,
    caplog,
) -> None:
    with caplog.at_level(logging.WARNING):
        configured = _build_configured_detectors(
            detector_config=get_default_issue_detector_config(),
            repository=cast(IssueRepository, _FakeRepository()),
            issue_category_ids=[999],
        )
    assert configured == []
    assert "Skipping unsupported issue_category_ids=[999]" in caplog.text
