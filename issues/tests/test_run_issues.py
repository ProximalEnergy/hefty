import datetime

from issues.orchestrator.run_issues import run_issues_backfill_for_projects
from issues.orchestrator.run_project import ProjectIssueRunSummary


def test_backfill_iterates_inclusive_days_with_project_local_boundaries(
    *,
    monkeypatch,
) -> None:
    call_times: list[datetime.datetime] = []
    overrides: list[int | None] = []
    passed_coordinates: list[tuple[float | None, float | None] | None] = []
    fixed_coords: tuple[float, float] = (35.0, -97.0)
    coordinate_query_count = 0

    def fake_load_project_coordinates(
        *,
        project_name_short: str,
    ) -> tuple[float | None, float | None]:
        nonlocal coordinate_query_count
        coordinate_query_count += 1
        assert project_name_short == "schema-a"
        return fixed_coords

    def fake_run_project_issues(
        *,
        project_id: str,
        run_time: datetime.datetime | None = None,
        issue_category_ids: list[int] | None = None,
        evaluation_window_minutes_override: int | None = None,
        project_coordinates: tuple[float | None, float | None] | None = None,
        config=None,
    ) -> ProjectIssueRunSummary:
        assert issue_category_ids == [10]
        assert run_time is not None
        assert project_coordinates == fixed_coords
        call_times.append(run_time)
        overrides.append(evaluation_window_minutes_override)
        passed_coordinates.append(project_coordinates)
        return ProjectIssueRunSummary(
            project_id=project_id,
            run_time=run_time,
            raw_candidate_count=0,
            final_candidate_count=0,
            opened_count=0,
            matched_count=0,
            resolved_count=0,
            active_count=0,
        )

    monkeypatch.setattr(
        "issues.orchestrator.run_issues._resolve_project_time_zone",
        lambda *, project_id: "America/Chicago",
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues.resolve_project_name_short",
        lambda project_id: "schema-a",
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues.load_project_coordinates",
        fake_load_project_coordinates,
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues.run_project_issues",
        fake_run_project_issues,
    )

    run_issues_backfill_for_projects(
        project_ids=["project-a"],
        issue_category_ids=[10],
        start=datetime.date(2026, 1, 1),
        end=datetime.date(2026, 1, 2),
    )

    assert call_times == [
        datetime.datetime(2026, 1, 2, 6, 0, tzinfo=datetime.UTC),
        datetime.datetime(2026, 1, 3, 6, 0, tzinfo=datetime.UTC),
    ]
    assert overrides == [24 * 60, 24 * 60]
    assert coordinate_query_count == 1
    assert passed_coordinates == [fixed_coords, fixed_coords]
