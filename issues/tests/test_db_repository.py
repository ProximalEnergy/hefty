import datetime
from typing import Any, Literal

from issues.models.issue_candidate import IssueCandidate, IssueIdentity
from issues.models.persistence_models import IssueRecord
from issues.persistence.db_repository import DbIssueRepository


class _FakeDb:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


class _FakeDbContext:
    def __init__(self, *, db: _FakeDb) -> None:
        self._db = db

    def __enter__(self) -> _FakeDb:
        return self._db

    def __exit__(self, *args: object) -> Literal[False]:
        return False


class _FakeWriteQuery:
    def __init__(self, *, operations: list[Any], kwargs: dict[str, Any]) -> None:
        self._operations = operations
        self._kwargs = kwargs

    def get(self, **kwargs: object) -> dict[str, int]:  # noqa: ARG002
        self._operations.append(self._kwargs)
        return {"issue_id": 1}


def _build_issue(
    *,
    issue_id: int,
    time_start: datetime.datetime,
    time_end: datetime.datetime | None = None,
) -> IssueRecord:
    return IssueRecord(
        issue_id=issue_id,
        device_id=10,
        tag_id=20,
        issue_category_id=30,
        time_start=time_start,
        time_end=time_end,
        detector_metadata={"detector_name": "test_detector"},
    )


def _build_candidate(*, time_start: datetime.datetime) -> IssueCandidate:
    return IssueCandidate(
        project_id="project-a",
        detector_name="test_detector",
        identity=IssueIdentity(device_id=10, tag_id=20, issue_category_id=30),
        time_start=time_start,
        detector_metadata={"detector_name": "test_detector", "fresh": True},
    )


def _patch_repository(
    *,
    monkeypatch,
    scoped_issues: list[IssueRecord],
) -> tuple[DbIssueRepository, _FakeDb, dict[str, list[Any]]]:
    repository = DbIssueRepository()
    operations: dict[str, list[Any]] = {
        "updates": [],
        "deletes": [],
        "closes": [],
        "creates": [],
        "issue_updates": [],
    }
    fake_db = _FakeDb()

    def fake_update_issue(**kwargs) -> _FakeWriteQuery:
        return _FakeWriteQuery(operations=operations["updates"], kwargs=kwargs)

    def fake_query_delete_issue(**kwargs) -> _FakeWriteQuery:
        return _FakeWriteQuery(operations=operations["deletes"], kwargs=kwargs)

    def fake_close_issue(**kwargs) -> _FakeWriteQuery:
        return _FakeWriteQuery(operations=operations["closes"], kwargs=kwargs)

    def fake_create_issue(**kwargs) -> _FakeWriteQuery:
        return _FakeWriteQuery(operations=operations["creates"], kwargs=kwargs)

    def fake_create_issue_update(**kwargs) -> _FakeWriteQuery:
        return _FakeWriteQuery(operations=operations["issue_updates"], kwargs=kwargs)

    monkeypatch.setattr(
        repository,
        "_load_scoped_issues",
        lambda **_: scoped_issues,
    )
    monkeypatch.setattr(
        repository,
        "_get_state_id",
        lambda *, state_name: 1 if state_name == "Open" else 2,
    )
    monkeypatch.setattr(repository, "_count_active_issues", lambda **_: 0)
    monkeypatch.setattr(
        "issues.persistence.db_repository.with_db",
        lambda *, schema: _FakeDbContext(db=fake_db),
    )
    monkeypatch.setattr(
        "issues.persistence.db_repository.crud.project.issues.update_issue",
        fake_update_issue,
    )
    monkeypatch.setattr(
        "issues.persistence.db_repository.crud.project.issues.query_delete_issue",
        fake_query_delete_issue,
    )
    monkeypatch.setattr(
        "issues.persistence.db_repository.crud.project.issues.close_issue",
        fake_close_issue,
    )
    monkeypatch.setattr(
        "issues.persistence.db_repository.crud.project.issues.create_issue",
        fake_create_issue,
    )
    monkeypatch.setattr(
        "issues.persistence.db_repository.crud.project.issues.create_issue_update",
        fake_create_issue_update,
    )
    return repository, fake_db, operations


def test_backfill_reconciliation_merges_duplicate_issues(*, monkeypatch) -> None:
    """Backfill keeps one issue row and deletes duplicate rows."""
    run_time = datetime.datetime(2026, 1, 2, 6, 0, tzinfo=datetime.UTC)
    window_start = run_time - datetime.timedelta(days=1)
    repository, fake_db, operations = _patch_repository(
        monkeypatch=monkeypatch,
        scoped_issues=[
            _build_issue(
                issue_id=1,
                time_start=window_start + datetime.timedelta(hours=1),
            ),
            _build_issue(
                issue_id=2,
                time_start=window_start + datetime.timedelta(minutes=30),
                time_end=run_time - datetime.timedelta(hours=1),
            ),
        ],
    )

    result = repository.apply_candidates(
        project_id="project-a",
        run_time=run_time,
        candidates=[_build_candidate(time_start=window_start)],
        reconciliation_window_minutes=24 * 60,
    )

    assert result.matched_count == 1
    assert fake_db.committed
    assert operations["updates"][0]["issue_id"] == 2
    assert operations["updates"][0]["values"]["time_start"] == window_start
    assert operations["updates"][0]["values"]["time_end"] is None
    assert operations["deletes"][0]["issue_id"] == 1
    assert operations["issue_updates"][0]["issue_update"]["issue_id"] == 2


def test_backfill_reconciliation_deletes_absent_issue(*, monkeypatch) -> None:
    """Backfill deletes overlapping issues that no longer have candidates."""
    run_time = datetime.datetime(2026, 1, 2, 6, 0, tzinfo=datetime.UTC)
    repository, _, operations = _patch_repository(
        monkeypatch=monkeypatch,
        scoped_issues=[_build_issue(issue_id=1, time_start=run_time)],
    )

    result = repository.apply_candidates(
        project_id="project-a",
        run_time=run_time,
        candidates=[],
        reconciliation_window_minutes=24 * 60,
    )

    assert result.resolved_count == 0
    assert operations["deletes"][0]["issue_id"] == 1
    assert operations["closes"] == []


def test_normal_run_resolves_absent_issue(*, monkeypatch) -> None:
    """Normal runs resolve absent open issues instead of deleting them."""
    run_time = datetime.datetime(2026, 1, 2, 6, 0, tzinfo=datetime.UTC)
    repository, _, operations = _patch_repository(
        monkeypatch=monkeypatch,
        scoped_issues=[_build_issue(issue_id=1, time_start=run_time)],
    )

    result = repository.apply_candidates(
        project_id="project-a",
        run_time=run_time,
        candidates=[],
    )

    assert result.resolved_count == 1
    assert operations["deletes"] == []
    assert operations["closes"][0]["issue_id"] == 1
    assert operations["issue_updates"][0]["issue_update"]["issue_id"] == 1
