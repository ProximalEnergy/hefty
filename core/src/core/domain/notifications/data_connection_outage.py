"""Data connection outage checks using project receive schedule vs last update time.

Primary API: :func:`get_project_ids_with_connection_outage` returns project IDs
split by outage status (``True`` / ``False`` keys).
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

import polars as pl
from sqlalchemy import outerjoin, select

from core import models
from core.db_query import DbQuery, OutputType


@dataclass(frozen=True)
class DataStatusCheck:
    """Expected collection window aligned with :func:`check_data_status`."""

    last_expected: datetime
    next_expected: datetime
    grace_period: timedelta


def _as_utc(*, dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _debug_instant_str(*, dt: datetime | None) -> str:
    """Format an instant for debug lines (ISO-8601, UTC, millisecond precision)."""
    if dt is None:
        return "None"
    return _as_utc(dt=dt).isoformat(timespec="milliseconds")


def _debug_time_row(*, label: str, dt: datetime | None) -> str:
    """One aligned debug line: ``label =`` padded, then the formatted instant."""
    left = f"{label} ="
    return f"    {left:<22}{_debug_instant_str(dt=dt)}"


def _outage_stale_minutes_for_debug(
    *,
    time_last: datetime | None,
    schedule: str | None,
    now: datetime,
) -> str:
    """Describe how stale the connection is when an outage is detected.

    Uses minutes between ``time_last`` and the minimum acceptable instant
    (``last_expected - grace``). Falls back to data age when cron cannot be
    parsed.

    Args:
        time_last: Last update from ``project_data_last_updated``.
        schedule: Project ``data_receive_schedule``, or ``None``.
        now: Current UTC instant used for the check.

    Returns:
        Short human-readable string for debug logs.
    """
    if time_last is None:
        return "n/a (no time_last)"
    tl = _as_utc(dt=time_last)
    if not schedule:
        age = (now - tl).total_seconds() / 60
        return f"{age:.2f} (data age; no schedule)"
    try:
        st = check_data_status(cron=schedule, now=now)
        thr = st.last_expected - st.grace_period
    except ValueError:
        age = (now - tl).total_seconds() / 60
        return f"{age:.2f} (data age; invalid cron)"
    behind_min = (thr - tl).total_seconds() / 60
    return f"{behind_min:.2f} (min before acceptable threshold)"


def check_data_status(*, cron: str, now: datetime) -> DataStatusCheck:
    """Derive last/next expected receive times and grace, matching web DataStatus.

    Supported cron formats (same as ``web-app`` ``checkDataStatus``):

    - Every minute: ``* * * * *``
    - Every N minutes: first field ``*/N`` (e.g. ``*/15 * * * *``)
    - Daily: ``MM HH * * *`` (minute hour, UTC)

    Args:
        cron: Schedule string from ``operational.projects.data_receive_schedule``.
        now: Current instant; normalized to UTC.

    Returns:
        Last expected receive, next expected receive, and grace period.

    Raises:
        ValueError: If the cron string is not supported.
    """
    now_utc = _as_utc(dt=now)
    minute_part = cron.split(" ")[0] if cron else ""

    if cron == "* * * * *":
        normalized = now_utc.replace(second=0, microsecond=0)
        last_expected = normalized
        next_expected = normalized + timedelta(minutes=1)
    elif minute_part.startswith("*/"):
        interval = int(minute_part[2:])
        normalized = now_utc.replace(second=0, microsecond=0)
        current_minute = normalized.minute
        last_minute = (current_minute // interval) * interval
        next_minute = last_minute + interval
        last_expected = normalized.replace(minute=last_minute)
        if next_minute < 60:
            next_expected = normalized.replace(minute=next_minute)
        else:
            next_expected = normalized.replace(minute=0, second=0, microsecond=0)
            next_expected += timedelta(hours=1)
    elif re.match(r"^\d+ \d+ \* \* \*$", cron):
        parts = cron.split()
        min_t, hour_t = int(parts[0]), int(parts[1])
        today = now_utc.replace(hour=hour_t, minute=min_t, second=0, microsecond=0)
        if now_utc < today:
            last_expected = today - timedelta(days=1)
            next_expected = today
        else:
            last_expected = today
            next_expected = today + timedelta(days=1)
    else:
        msg = f"Unsupported cron format: {cron}"
        raise ValueError(msg)

    span = next_expected - last_expected
    hour_ms = timedelta(hours=1).total_seconds() * 1000
    grace_ms = min(span.total_seconds() * 1000, hour_ms)
    grace_period = timedelta(milliseconds=grace_ms)

    return DataStatusCheck(
        last_expected=last_expected,
        next_expected=next_expected,
        grace_period=grace_period,
    )


def is_connection_outage(
    *,
    data_receive_schedule: str | None,
    time_last: datetime | None,
    now: datetime,
) -> bool | None:
    """Whether data is late vs schedule (``None`` = cannot decide: missing schedule).

    Args:
        data_receive_schedule: Project cron cadence, or ``None``.
        time_last: Last data timestamp from ``project_data_last_updated``, or ``None``.
        now: Current UTC time to compare against.

    Returns:
        ``True`` if outage, ``False`` if OK, ``None`` if schedule is missing.
    """
    if not data_receive_schedule:
        return None
    if time_last is None:
        return True
    try:
        status = check_data_status(cron=data_receive_schedule, now=now)
    except ValueError:
        return True
    time_last_utc = _as_utc(dt=time_last)
    threshold = status.last_expected - status.grace_period
    return time_last_utc < threshold


async def _load_projects_for_connection_outage(
    *,
    now: datetime | None = None,
) -> tuple[datetime, pl.DataFrame]:
    """Load schedule and ``time_last`` for every project (outer join)."""
    stmt = select(
        models.Project.project_id,
        models.Project.name_short,
        models.Project.data_receive_schedule,
        models.ProjectDataLastUpdated.time_last,
    ).select_from(
        outerjoin(
            models.Project,
            models.ProjectDataLastUpdated,
            models.Project.project_id == models.ProjectDataLastUpdated.project_id,
        )
    )
    query: DbQuery[Any, Literal[False]] = DbQuery(query=stmt)
    result = await query.get_async(output_type=OutputType.POLARS)
    current = _as_utc(dt=now) if now is not None else datetime.now(UTC)
    return current, result


async def get_data_connection_outage_project_ids(
    *,
    now: datetime | None = None,
) -> dict[bool, list[UUID]]:
    """Split project IDs by connection-outage status.

    Args:
        now: Reference instant (UTC); defaults to real-time.

    Returns:
        ``{True: [...], False: [...]}``. ``True`` = :func:`is_connection_outage`
        is ``True`` (late vs schedule). ``False`` = not an outage: either
        :func:`is_connection_outage` is ``False`` (on time) or ``None`` (no
        ``data_receive_schedule``, so outage cannot be determined).
    """
    current, result = await _load_projects_for_connection_outage(now=now)
    out: dict[bool, list[UUID]] = {True: [], False: []}
    for row in result.iter_rows(named=True):
        outage = is_connection_outage(
            data_receive_schedule=row["data_receive_schedule"],
            time_last=row["time_last"],
            now=current,
        )
        if outage is True:
            out[True].append(row["project_id"])
        else:
            out[False].append(row["project_id"])
    return out


async def print_data_connection_outage_status(
    *,
    now: datetime | None = None,
    debug: bool = True,
) -> None:
    """Print per-project outage status (optional verbose debug).

    For programmatic use, prefer :func:`get_project_ids_with_connection_outage`.

    Args:
        now: Instant to use as current UTC time; defaults to real-time UTC.
        debug: When True, print run summary and per-project schedule/threshold detail.
    """
    current, result = await _load_projects_for_connection_outage(now=now)

    if debug:
        print(  # noqa: T201
            "data_connection_outage: "
            f"now_utc={_debug_instant_str(dt=current)} "
            f"project_rows={result.height}"
        )

    for row in result.iter_rows(named=True):
        project_id = row["project_id"]
        name_short = row["name_short"]
        schedule = row["data_receive_schedule"]
        time_last = row["time_last"]

        outage = is_connection_outage(
            data_receive_schedule=schedule,
            time_last=time_last,
            now=current,
        )

        if debug:
            print(f"--- project_id={project_id} name_short={name_short!r}")  # noqa: T201
            print(f"    data_receive_schedule={schedule!r}")  # noqa: T201
            print(_debug_time_row(label="time_last_utc", dt=time_last))  # noqa: T201
            if schedule:
                try:
                    st = check_data_status(cron=schedule, now=current)
                    thr = st.last_expected - st.grace_period
                    print(  # noqa: T201
                        _debug_time_row(label="last_expected_utc", dt=st.last_expected)
                    )
                    print(  # noqa: T201
                        _debug_time_row(label="next_expected_utc", dt=st.next_expected)
                    )
                    gp = "grace_period ="
                    print(f"    {gp:<22}{st.grace_period}")  # noqa: T201
                    print(_debug_time_row(label="threshold_utc", dt=thr))  # noqa: T201
                except ValueError as exc:
                    print(f"    cron_parse_error={exc!r}")  # noqa: T201
            print(f"    is_outage={outage!r}")  # noqa: T201
            if outage is True:
                stale = _outage_stale_minutes_for_debug(
                    time_last=time_last,
                    schedule=schedule,
                    now=current,
                )
                print(f"    outage_stale_minutes={stale}")  # noqa: T201

        if outage is None:
            print(  # noqa: T201
                f"{project_id}: unknown (no data_receive_schedule)"
            )
        elif outage:
            print(f"{project_id}: outage")  # noqa: T201
        else:
            print(f"{project_id}: ok")  # noqa: T201
