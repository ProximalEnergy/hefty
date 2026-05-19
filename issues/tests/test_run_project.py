import logging
from typing import cast

from issues.config.issue_detectors import get_default_issue_detector_config
from issues.orchestrator.run_project import (
    _build_configured_detectors,
    run_project_issues,
)
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


def test_run_project_issues_uses_provided_project_name_short(*, monkeypatch) -> None:
    """Pre-resolved project schemas skip project id metadata lookup."""
    monkeypatch.setattr(
        "issues.orchestrator.run_project.resolve_project_name_short",
        lambda *, project_id: (_ for _ in ()).throw(
            AssertionError("Should not resolve project_name_short when provided")
        ),
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_project.build_issue_repository",
        lambda *, project_name_short: cast(IssueRepository, _FakeRepository()),
    )

    summary = run_project_issues(
        project_id="project-a",
        project_name_short="schema-a",
        issue_category_ids=[999],
    )

    assert summary.project_id == "project-a"
    assert summary.raw_candidate_count == 0
