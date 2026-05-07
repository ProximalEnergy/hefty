import datetime

import pytest

from issues.lambda_handler import (
    parse_backfill_date,
    parse_issue_category_ids,
    validate_backfill_arguments,
)


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
