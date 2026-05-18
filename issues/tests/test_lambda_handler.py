import datetime
import json

import pytest

from issues.lambda_handler import (
    lambda_handler,
    parse_backfill_date,
    parse_issue_category_ids,
    validate_backfill_arguments,
)
from issues.orchestrator.run_project import ProjectIssueRunSummary


def test_parse_issue_category_ids_accepts_none() -> None:
    assert parse_issue_category_ids(value=None) is None


def test_parse_issue_category_ids_parses_ints() -> None:
    parsed = parse_issue_category_ids(value=[1, "2", "", None])
    assert parsed == [1, 2]


def test_parse_backfill_date_requires_iso_date() -> None:
    with pytest.raises(ValueError, match="start must be an ISO-8601 date string"):
        parse_backfill_date(value="2026/01/01", field_name="start")


def test_validate_backfill_requires_dates_when_scope_is_passed() -> None:
    with pytest.raises(
        ValueError,
        match="start and end are required when passing backfill scope arguments",
    ):
        validate_backfill_arguments(
            project_ids=["project-a"],
            issue_category_ids=None,
            start=None,
            end=None,
        )


def test_validate_backfill_rejects_start_after_end() -> None:
    with pytest.raises(ValueError, match="start must be less than or equal to end"):
        validate_backfill_arguments(
            project_ids=None,
            issue_category_ids=None,
            start=datetime.date(2026, 1, 3),
            end=datetime.date(2026, 1, 1),
        )


def test_lambda_handler_routes_scheduled_event_to_standard_run(
    *,
    monkeypatch,
) -> None:
    run_times: list[datetime.datetime | None] = []

    def fake_discover_project_ids() -> list[str]:
        return ["project-a"]

    def fake_run_issues_for_projects(
        *,
        project_ids: list[str] | None = None,
        run_time: datetime.datetime | None = None,
        issue_category_ids: list[int] | None = None,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
    ) -> list[ProjectIssueRunSummary]:
        assert project_ids == ["project-a"]
        assert issue_category_ids is None
        assert start is None
        assert end is None
        run_times.append(run_time)
        assert run_time is not None
        return [
            ProjectIssueRunSummary(
                project_id="project-a",
                run_time=run_time,
                raw_candidate_count=0,
                final_candidate_count=0,
                opened_count=0,
                matched_count=0,
                resolved_count=0,
                active_count=0,
            )
        ]

    monkeypatch.setattr(
        "issues.lambda_handler.configure_lambda_logging",
        lambda: None,
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues.discover_project_ids",
        fake_discover_project_ids,
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues.run_issues_for_projects",
        fake_run_issues_for_projects,
    )

    response = lambda_handler(
        {
            "source": "aws.events",
            "detail-type": "Scheduled Event",
            "time": "2026-01-02T06:00:00Z",
        },
        None,
    )

    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert body["project_count"] == 1
    assert body["failure_count"] == 0
    assert run_times == [datetime.datetime(2026, 1, 2, 6, 0, tzinfo=datetime.UTC)]
