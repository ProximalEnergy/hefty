import datetime

from issues.orchestrator.run_issues import (
    ProjectRunMetadata,
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
    """Backfill uses bulk metadata across inclusive project-local days."""
    call_times: list[datetime.datetime] = []
    overrides: list[int | None] = []
    passed_coordinates: list[tuple[float | None, float | None] | None] = []
    passed_name_shorts: list[str | None] = []
    fixed_coords: tuple[float, float] = (35.0, -97.0)

    def fake_run_project_issues(
        *,
        project_id: str,
        run_time: datetime.datetime | None = None,
        issue_category_ids: list[int] | None = None,
        evaluation_window_minutes_override: int | None = None,
        project_name_short: str | None = None,
        project_coordinates: tuple[float | None, float | None] | None = None,
        config=None,
    ) -> ProjectIssueRunSummary:
        assert issue_category_ids == [10]
        assert run_time is not None
        assert project_name_short == "schema-a"
        assert project_coordinates == fixed_coords
        call_times.append(run_time)
        overrides.append(evaluation_window_minutes_override)
        passed_name_shorts.append(project_name_short)
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
        "issues.orchestrator.run_issues._load_project_metadata_by_identifier",
        lambda *, project_ids: {
            "project-a": ProjectRunMetadata(
                name_short="schema-a",
                time_zone="America/Chicago",
                coordinates=fixed_coords,
            )
        },
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
    assert passed_name_shorts == ["schema-a", "schema-a"]
    assert passed_coordinates == [fixed_coords, fixed_coords]


def test_floor_to_five_minute_boundary_rounds_down() -> None:
    """Run times floor down to the prior five-minute boundary."""
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
    """Default runs floor current time before dispatching projects."""
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
    monkeypatch.setattr(
        "issues.orchestrator.run_issues._load_project_metadata_by_identifier",
        lambda *, project_ids: {
            "project-a": ProjectRunMetadata(
                name_short="schema-a",
                time_zone="America/Chicago",
                coordinates=(35.0, -97.0),
            )
        },
    )

    def fake_run_projects_once(
        *,
        project_ids: list[str],
        run_time: datetime.datetime,
        issue_category_ids: list[int] | None,
        evaluation_window_minutes_override: int | None = None,
        project_coordinates: tuple[float | None, float | None] | None = None,
        project_metadata_by_identifier: dict[str, ProjectRunMetadata] | None = None,
    ) -> list[ProjectIssueRunSummary]:
        assert project_ids == ["project-a"]
        assert issue_category_ids is None
        assert evaluation_window_minutes_override is None
        assert project_coordinates is None
        assert project_metadata_by_identifier is not None
        passed_run_times.append(run_time)
        return []

    monkeypatch.setattr(
        "issues.orchestrator.run_issues._run_projects_once",
        fake_run_projects_once,
    )

    run_issues_for_projects()

    assert passed_run_times == [floored_run_time]


def test_run_issues_for_projects_keeps_explicit_run_time(*, monkeypatch) -> None:
    """Explicit run times are forwarded without flooring."""
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
    monkeypatch.setattr(
        "issues.orchestrator.run_issues._load_project_metadata_by_identifier",
        lambda *, project_ids: {
            "project-a": ProjectRunMetadata(
                name_short="schema-a",
                time_zone="America/Chicago",
                coordinates=(35.0, -97.0),
            )
        },
    )

    def fake_run_projects_once(
        *,
        project_ids: list[str],
        run_time: datetime.datetime,
        issue_category_ids: list[int] | None,
        evaluation_window_minutes_override: int | None = None,
        project_coordinates: tuple[float | None, float | None] | None = None,
        project_metadata_by_identifier: dict[str, ProjectRunMetadata] | None = None,
    ) -> list[ProjectIssueRunSummary]:
        assert project_ids == ["project-a"]
        assert issue_category_ids is None
        assert evaluation_window_minutes_override is None
        assert project_coordinates is None
        assert project_metadata_by_identifier is not None
        passed_run_times.append(run_time)
        return []

    monkeypatch.setattr(
        "issues.orchestrator.run_issues._run_projects_once",
        fake_run_projects_once,
    )

    run_issues_for_projects(run_time=explicit_run_time)

    assert passed_run_times == [explicit_run_time]


def test_run_issues_for_projects_runs_midnight_backfill_per_project(
    *,
    monkeypatch,
) -> None:
    """Default runs split midnight backfills per project timezone."""
    run_time = datetime.datetime(2026, 1, 2, 6, 0, tzinfo=datetime.UTC)
    backfill_calls: list[
        tuple[list[str], list[int] | None, datetime.date, datetime.date]
    ] = []
    normal_calls: list[tuple[list[str], datetime.datetime, list[int] | None]] = []

    def fake_run_backfill_for_project_days(
        *,
        project_id: str,
        issue_category_ids: list[int] | None,
        start: datetime.date,
        end: datetime.date,
        time_zone: str,
        project_metadata: ProjectRunMetadata | None,
    ) -> list[ProjectIssueRunSummary]:
        assert time_zone == "America/Chicago"
        assert project_metadata is not None
        assert project_metadata.coordinates == (35.0, -97.0)
        backfill_calls.append(([project_id], issue_category_ids, start, end))
        return [
            ProjectIssueRunSummary(
                project_id=project_id,
                run_time=run_time,
                raw_candidate_count=0,
                final_candidate_count=0,
                opened_count=0,
                matched_count=0,
                resolved_count=0,
                active_count=0,
            )
        ]

    def fake_run_projects_once(
        *,
        project_ids: list[str],
        run_time: datetime.datetime,
        issue_category_ids: list[int] | None,
        evaluation_window_minutes_override: int | None = None,
        project_coordinates: tuple[float | None, float | None] | None = None,
        project_metadata_by_identifier: dict[str, ProjectRunMetadata] | None = None,
    ) -> list[ProjectIssueRunSummary]:
        assert evaluation_window_minutes_override is None
        assert project_coordinates is None
        assert project_metadata_by_identifier is not None
        normal_calls.append((project_ids, run_time, issue_category_ids))
        return [
            ProjectIssueRunSummary(
                project_id=project_id,
                run_time=run_time,
                raw_candidate_count=0,
                final_candidate_count=0,
                opened_count=0,
                matched_count=0,
                resolved_count=0,
                active_count=0,
            )
            for project_id in project_ids
        ]

    project_lookup = {
        "project-a": ProjectRunMetadata(
            name_short="schema-a",
            time_zone="America/Chicago",
            coordinates=(35.0, -97.0),
        ),
        "project-b": ProjectRunMetadata(
            name_short="schema-b",
            time_zone="America/New_York",
            coordinates=(36.0, -98.0),
        ),
    }
    monkeypatch.setattr(
        "issues.orchestrator.run_issues._load_project_metadata_by_identifier",
        lambda *, project_ids: project_lookup,
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues._run_backfill_for_project_days",
        fake_run_backfill_for_project_days,
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues._run_projects_once",
        fake_run_projects_once,
    )

    summaries = run_issues_for_projects(
        project_ids=["project-a", "project-b"],
        run_time=run_time,
        issue_category_ids=[10],
    )

    assert [summary.project_id for summary in summaries] == ["project-a", "project-b"]
    assert backfill_calls == [
        (
            ["project-a"],
            [10],
            datetime.date(2026, 1, 1),
            datetime.date(2026, 1, 1),
        )
    ]
    assert normal_calls == [(["project-b"], run_time, [10])]


def test_run_issues_for_projects_preserves_explicit_backfill(
    *,
    monkeypatch,
) -> None:
    """Explicit backfills bypass default hourly project splitting."""
    calls: list[tuple[list[str], list[int] | None, datetime.date, datetime.date]] = []

    def fake_run_issues_backfill_for_projects(
        *,
        project_ids: list[str],
        issue_category_ids: list[int] | None,
        start: datetime.date,
        end: datetime.date,
    ) -> list[ProjectIssueRunSummary]:
        calls.append((project_ids, issue_category_ids, start, end))
        return []

    monkeypatch.setattr(
        "issues.orchestrator.run_issues.run_issues_backfill_for_projects",
        fake_run_issues_backfill_for_projects,
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues._run_default_project_scope",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("Default path should not run explicit backfills")
        ),
    )

    run_issues_for_projects(
        project_ids=["project-a"],
        issue_category_ids=[10],
        start=datetime.date(2026, 1, 1),
        end=datetime.date(2026, 1, 2),
    )

    assert calls == [
        (
            ["project-a"],
            [10],
            datetime.date(2026, 1, 1),
            datetime.date(2026, 1, 2),
        )
    ]


def test_local_midnight_backfill_runs_previous_day_for_midnight_projects(
    *,
    monkeypatch,
) -> None:
    """Local-midnight helper backfills only projects at midnight."""
    calls: list[tuple[str, list[int] | None, datetime.date, datetime.date]] = []

    def fake_run_backfill_for_project_days(
        *,
        project_id: str,
        issue_category_ids: list[int] | None,
        start: datetime.date,
        end: datetime.date,
        time_zone: str,
        project_metadata: ProjectRunMetadata | None,
    ) -> list[ProjectIssueRunSummary]:
        assert time_zone == "America/Chicago"
        assert project_metadata is not None
        calls.append((project_id, issue_category_ids, start, end))
        return [
            ProjectIssueRunSummary(
                project_id=project_id,
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
        "issues.orchestrator.run_issues._load_project_metadata_by_identifier",
        lambda *, project_ids: {
            "project-a": ProjectRunMetadata(
                name_short="schema-a",
                time_zone="America/Chicago",
                coordinates=(35.0, -97.0),
            ),
            "project-b": ProjectRunMetadata(
                name_short="schema-b",
                time_zone="America/New_York",
                coordinates=(36.0, -98.0),
            ),
        },
    )
    monkeypatch.setattr(
        "issues.orchestrator.run_issues._run_backfill_for_project_days",
        fake_run_backfill_for_project_days,
    )

    summaries = run_local_midnight_backfill_for_projects(
        project_ids=["project-a", "project-b"],
        run_time=datetime.datetime(2026, 1, 2, 6, 0, tzinfo=datetime.UTC),
    )

    assert [summary.project_id for summary in summaries] == ["project-a"]
    assert calls == [
        (
            "project-a",
            None,
            datetime.date(2026, 1, 1),
            datetime.date(2026, 1, 1),
        )
    ]
