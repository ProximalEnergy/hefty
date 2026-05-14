import datetime

from issues.orchestrator.run_issues import (
    _floor_to_five_minute_boundary,
    run_issues_backfill_for_projects,
    run_issues_for_projects,
    run_local_midnight_backfill_for_projects,
)
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


def test_floor_to_five_minute_boundary_rounds_down() -> None:
    value = datetime.datetime(2026, 5, 8, 13, 42, 39, 1200, tzinfo=datetime.UTC)

    assert _floor_to_five_minute_boundary(value=value) == datetime.datetime(
        2026,
        5,
        8,
        13,
        40,
        tzinfo=datetime.UTC,
    )


def test_run_issues_for_projects_floors_default_run_time(*, monkeypatch) -> None:
    passed_run_times: list[datetime.datetime] = []
    floored_run_time = datetime.datetime(2026, 5, 8, 13, 40, tzinfo=datetime.UTC)

    monkeypatch.setattr(
        "issues.orchestrator.run_issues.discover_project_ids",
        lambda: ["project-a"],
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues._floor_to_five_minute_boundary",
        lambda *, value: floored_run_time,
    )

    def fake_run_projects_once(
        *,
        project_ids: list[str],
        run_time: datetime.datetime,
        issue_category_ids: list[int] | None,
        evaluation_window_minutes_override: int | None = None,
        project_coordinates: tuple[float | None, float | None] | None = None,
    ) -> list[ProjectIssueRunSummary]:
        assert project_ids == ["project-a"]
        assert issue_category_ids is None
        assert evaluation_window_minutes_override is None
        assert project_coordinates is None
        passed_run_times.append(run_time)
        return []

    monkeypatch.setattr(
        "issues.orchestrator.run_issues._run_projects_once",
        fake_run_projects_once,
    )

    run_issues_for_projects()

    assert passed_run_times == [floored_run_time]


def test_run_issues_for_projects_keeps_explicit_run_time(*, monkeypatch) -> None:
    passed_run_times: list[datetime.datetime] = []
    explicit_run_time = datetime.datetime(
        2026,
        5,
        8,
        13,
        42,
        39,
        tzinfo=datetime.UTC,
    )

    monkeypatch.setattr(
        "issues.orchestrator.run_issues.discover_project_ids",
        lambda: ["project-a"],
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues._floor_to_five_minute_boundary",
        lambda *, value: (_ for _ in ()).throw(
            AssertionError("Should not floor explicit run_time")
        ),
    )

    def fake_run_projects_once(
        *,
        project_ids: list[str],
        run_time: datetime.datetime,
        issue_category_ids: list[int] | None,
        evaluation_window_minutes_override: int | None = None,
        project_coordinates: tuple[float | None, float | None] | None = None,
    ) -> list[ProjectIssueRunSummary]:
        assert project_ids == ["project-a"]
        assert issue_category_ids is None
        assert evaluation_window_minutes_override is None
        assert project_coordinates is None
        passed_run_times.append(run_time)
        return []

    monkeypatch.setattr(
        "issues.orchestrator.run_issues._run_projects_once",
        fake_run_projects_once,
    )

    run_issues_for_projects(run_time=explicit_run_time)

    assert passed_run_times == [explicit_run_time]


def test_local_midnight_backfill_runs_previous_day_for_midnight_projects(
    *,
    monkeypatch,
) -> None:
    calls: list[tuple[list[str], list[int] | None, datetime.date, datetime.date]] = []

    def fake_run_issues_backfill_for_projects(
        *,
        project_ids: list[str],
        issue_category_ids: list[int] | None,
        start: datetime.date,
        end: datetime.date,
    ) -> list[ProjectIssueRunSummary]:
        calls.append((project_ids, issue_category_ids, start, end))
        return [
            ProjectIssueRunSummary(
                project_id=project_ids[0],
                run_time=datetime.datetime(2026, 1, 2, 6, 0, tzinfo=datetime.UTC),
                raw_candidate_count=0,
                final_candidate_count=0,
                opened_count=0,
                matched_count=0,
                resolved_count=0,
                active_count=0,
            )
        ]

    monkeypatch.setattr(
        "issues.orchestrator.run_issues._resolve_project_time_zone",
        lambda *, project_id: (
            "America/Chicago" if project_id == "project-a" else "America/New_York"
        ),
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues.run_issues_backfill_for_projects",
        fake_run_issues_backfill_for_projects,
    )

    summaries = run_local_midnight_backfill_for_projects(
        project_ids=["project-a", "project-b"],
        run_time=datetime.datetime(2026, 1, 2, 6, 0, tzinfo=datetime.UTC),
    )

    assert [summary.project_id for summary in summaries] == ["project-a"]
    assert calls == [
        (
            ["project-a"],
            None,
            datetime.date(2026, 1, 1),
            datetime.date(2026, 1, 1),
        )
    ]
