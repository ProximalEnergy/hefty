import asyncio
import datetime
import logging
import traceback
import uuid
from typing import Annotated, Any
from zoneinfo import ZoneInfo

import pandas as pd
import sentry_sdk
from core.crud.operational.device_types import get_device_types
from core.crud.operational.failure_modes import get_failure_modes
from core.crud.project import events as core_events
from core.db_query import OutputType
from core.dependencies import get_db
from core.enumerations import DeviceType, EventLossType, ProjectType, SensorType
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import interfaces, utils
from app._crud.operational.failure_modes import get_root_causes
from app._crud.operational.failure_modes import (
    update_event_root_cause as crud_update_event_root_cause,
)
from app._crud.projects.drone_anomalies import bulk_update_anomalies_with_event_ids
from app._crud.projects.drone_anomalies import (
    get_anomalies_by_event_id as crud_get_anomalies_by_event_id,
)
from app.dependencies import (
    get_async_db,
    get_project_api,
    get_project_db,
    get_project_db_async,
    get_project_name_short,
)
from core import models

router = APIRouter(prefix="/projects/{project_id}/events", tags=["project_events"])


def _none_if_nan(x: Any) -> float | None:  # nosemgrep: python-enforce-keyword-only-args
    """todo

    Args:
        x: TODO: describe.
    """
    if x is None:
        return None
    try:
        return None if pd.isna(x) else float(x)
    except (TypeError, ValueError):
        return None


@router.get("", response_model=list[interfaces.Event])
async def get_events(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    project_db: Annotated[Session, Depends(get_project_db)],
    project_id: uuid.UUID,
    device_id: int | None = None,
    time_end_gte: datetime.datetime | None = None,
    time_end_lt: datetime.datetime | None = None,
    open: bool = True,
    event_ids: Annotated[list[int] | None, Query()] = None,
    open_at: datetime.datetime | None = None,
) -> list[interfaces.Event] | None:
    """todo

    Args:
        db: TODO: describe.
        project_db: TODO: describe.
        project_id: TODO: describe.
        device_id: TODO: describe.
        time_end_gte: TODO: describe.
        time_end_lt: TODO: describe.
        open: TODO: describe.
        event_ids: TODO: describe.
        open_at: TODO: describe.
    """
    if device_id == -1:
        return None

    project_name_short = get_project_name_short(project_id=project_id)
    if not project_name_short:
        raise HTTPException(status_code=404, detail="Project not found")

    # Use the CRUD function to get events with device information
    events_query = core_events.get_events_with_device_info(
        device_id=device_id,
        time_end_gte=time_end_gte,
        time_end_lt=time_end_lt,
        open=open,
        event_ids=event_ids,
        open_at=open_at,
    )
    events_df = await events_query.get_async(
        schema=project_name_short,
        output_type=OutputType.POLARS,
    )
    if events_df is None or events_df.is_empty():
        return []
    events = events_df.to_dicts()

    if len(events) == 0:
        return []

    # Collect IDs
    failure_mode_ids = list(
        {e["failure_mode_id"] for e in events if e.get("failure_mode_id") is not None}
    )
    root_cause_ids = list(
        {e["root_cause_id"] for e in events if e.get("root_cause_id") is not None}
    )

    # Fetch Failure Modes and Root Causes
    failure_modes_task = get_failure_modes(failure_mode_ids=failure_mode_ids).get_async(
        output_type=OutputType.SQLALCHEMY
    )

    root_causes_task = get_root_causes(db=db, root_cause_ids=root_cause_ids)

    failure_modes, root_causes = await asyncio.gather(
        failure_modes_task, root_causes_task
    )

    # Create mappings
    failure_mode_map = {
        fm.failure_mode_id: interfaces.FailureMode(
            failure_mode_id=fm.failure_mode_id,
            device_type_id=fm.device_type_id,
            name_short=fm.name_short,
            name_long=fm.name_long,
        )
        for fm in failure_modes
    }

    root_cause_map = {
        rc.root_cause_id: interfaces.RootCause(
            root_cause_id=rc.root_cause_id,
            device_type_id=rc.device_type_id,
            name_short=rc.name_short,
            name_long=rc.name_long,
        )
        for rc in root_causes
    }

    # Process the results using a more efficient approach
    result: list[interfaces.Event] = []
    for event in events:
        device_type_name = event.get("device_type_name_long") or "Unknown"
        device_name = event.get("device_name_long") or ""
        device_name_full = f"{device_type_name} {device_name}"

        event_dict = dict(event)
        event_dict.pop("device_type_name_long", None)
        event_dict.pop("device_name_long", None)

        event_dict["device_name_full"] = device_name_full

        if event_dict.get("failure_mode_id") in failure_mode_map:
            event_dict["failure_mode"] = failure_mode_map[event_dict["failure_mode_id"]]

        if event_dict.get("root_cause_id") in root_cause_map:
            event_dict["root_cause"] = root_cause_map[event_dict["root_cause_id"]]

        result.append(interfaces.Event(**event_dict))

    return result


@router.get("/paginated-events", response_model=list[interfaces.PaginatedEvent])
async def get_paginated_events(
    project_id: uuid.UUID,
    page: int,
    page_size: int = 20,
    sort_column: str = "time_start",
    sort_direction: str = "desc",
    open: bool = True,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    device_type_ids: Annotated[list[int] | None, Query()] = None,
    device_ids: Annotated[list[int] | None, Query()] = None,
    project_db: Session = Depends(get_project_db),
    db: AsyncSession = Depends(get_async_db),
) -> list[interfaces.PaginatedEvent]:
    # Get paginated events with single query
    """todo

    Args:
        project_id: TODO: describe.
        page: TODO: describe.
        page_size: TODO: describe.
        sort_column: TODO: describe.
        sort_direction: TODO: describe.
        open: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        device_type_ids: TODO: describe.
        device_ids: TODO: describe.
        project_db: TODO: describe.
        db: TODO: describe.
    """
    project_name_short = get_project_name_short(project_id=project_id)
    if not project_name_short:
        raise HTTPException(status_code=404, detail="Project not found")

    data_query = core_events.get_paginated_events(
        page=page,
        page_size=page_size,
        sort_column=sort_column,
        sort_direction=sort_direction,
        open=open,
        device_type_id=device_type_ids,  # preserve existing behavior/signature
        device_ids=device_ids,
        start=start,
        end=end,
    )
    data_df = await data_query.get_async(
        schema=project_name_short,
        output_type=OutputType.POLARS,
    )
    if data_df is None or data_df.is_empty():
        return []
    data = data_df.to_dicts()

    if not data:
        return []

    event_objs = data

    event_ids = [int(e["event_id"]) for e in event_objs]
    device_ids_only = [int(e["device_id"]) for e in event_objs]

    # Root causes: fetch only those referenced (minor efficiency boost; same behavior)
    root_cause_ids: list[int] = [
        int(e["root_cause_id"]) for e in event_objs if e["root_cause_id"] is not None
    ]

    root_causes = await get_root_causes(
        db=db,
        root_cause_ids=root_cause_ids if root_cause_ids else [],
    )

    root_cause_id_to_name = {rc.root_cause_id: rc.name_long for rc in root_causes}

    # Devices and types
    devices = core.crud.project.devices.get_project_devices(
        project_db, device_ids=device_ids_only
    ).models()
    device_dict = {d.device_id: d for d in devices}

    device_type_ids_only: list[int] = [
        int(d.device_type_id) for d in devices if d.device_type_id is not None
    ]

    device_types = await get_device_types(
        db=db,
        device_type_ids=device_type_ids_only if device_type_ids_only else [],
    )

    device_type_dict = {dt.device_type_id: dt for dt in device_types}

    # Precompute full device names
    device_name_full_by_event: dict[uuid.UUID, str] = {}
    for e in event_objs:
        d = device_dict.get(e["device_id"])
        if d:
            dt = device_type_dict.get(d.device_type_id)
            if dt:
                device_name_full_by_event[e["event_id"]] = (
                    f"{dt.name_long} {d.name_long or ''}"
                )

    # Losses (pivot once, NaN -> None)
    losses_df = await core.crud.project.event_losses.get_event_losses(
        event_ids=event_ids,
    ).get_async(
        schema=project_name_short,
        output_type=OutputType.PANDAS,
    )

    # If no losses, keep existing behavior
    if losses_df.empty:
        losses_map: dict = {}
    else:
        # Ensure expected columns exist
        cols_needed = {"event_id", "event_loss_type_id", "loss", "time"}
        missing = cols_needed - set(losses_df.columns)
        if missing:
            raise RuntimeError(f"event_losses missing columns: {missing}")

        # 1) per (event, type) totals + data-span
        g = losses_df.groupby(["event_id", "event_loss_type_id"], as_index=False).agg(
            total_loss=("loss", "sum"), tmin=("time", "min"), tmax=("time", "max")
        )
        g["days_data_span"] = (
            g["tmax"].dt.floor("D") - g["tmin"].dt.floor("D")
        ).dt.days + 1

        # 2) per event duration (event-based denominator)
        ev = pd.DataFrame(
            [
                {
                    "event_id": e["event_id"],
                    "time_start": e["time_start"],
                    "time_end": e["time_end"]
                    or datetime.datetime.now(e["time_start"].tzinfo),
                }
                for e in event_objs
            ]
        )
        # Align tz and floor to whole days if you want calendar-aware durations
        ev["days_event"] = (
            ev["time_end"].dt.floor("D") - ev["time_start"].dt.floor("D")
        ).dt.days + 1

        # 3) choose denominator: event duration (matches your refactor)
        g = g.merge(ev[["event_id", "days_event"]], on="event_id", how="left")
        denom = g["days_event"]  # or g["days_data_span"] for original behavior

        g["avg_loss_per_day"] = g["total_loss"] / denom.replace({0: pd.NA})

        # 4) pivot once
        totals = g.pivot(
            index="event_id", columns="event_loss_type_id", values="total_loss"
        )
        dailies = g.pivot(
            index="event_id", columns="event_loss_type_id", values="avg_loss_per_day"
        )

        # 5) build losses_map in O(E)
        losses_map = {}
        has = lambda frame, col: (frame is not None) and (
            col in getattr(frame, "columns", [])
        )
        for ev_id in set(g["event_id"]):
            losses_map[ev_id] = {
                "loss_total_power": _none_if_nan(
                    totals.at[ev_id, 1]
                    if has(totals, 1) and ev_id in totals.index
                    else None
                ),
                "loss_total_financial": _none_if_nan(
                    totals.at[ev_id, 2]
                    if has(totals, 2) and ev_id in totals.index
                    else None
                ),
                "loss_daily_power": _none_if_nan(
                    dailies.at[ev_id, 1]
                    if has(dailies, 1) and ev_id in dailies.index
                    else None
                ),
                "loss_daily_financial": _none_if_nan(
                    dailies.at[ev_id, 2]
                    if has(dailies, 2) and ev_id in dailies.index
                    else None
                ),
            }

    # Build response
    out: list[interfaces.PaginatedEvent] = []
    for e in event_objs:
        ev_id = e["event_id"]
        name_full = device_name_full_by_event.get(ev_id, "Unknown")
        loss_vals = losses_map.get(ev_id, {})

        out.append(
            interfaces.PaginatedEvent(
                event_id=ev_id,
                device_name_full=name_full,
                time_start=e["time_start"],
                time_end=e["time_end"],
                # per original code, "today" fields are constant zeros
                loss_daily_power=loss_vals.get("loss_daily_power"),
                loss_today_power=0,
                loss_total_power=loss_vals.get("loss_total_power"),
                loss_daily_financial=loss_vals.get("loss_daily_financial"),
                loss_today_financial=0,
                loss_total_financial=loss_vals.get("loss_total_financial"),
                root_cause=root_cause_id_to_name.get(e["root_cause_id"]) or "Unknown",
            )
        )

    return out


@router.put("/{event_id}/root-cause")
async def update_event_root_cause(
    root_cause: Annotated[interfaces.RootCauseUpdate, Body()],
    event_id: Annotated[int, Path(title="The ID of the event to update")],
    project_db: AsyncSession = Depends(get_project_db_async),
):
    """todo

    Args:
        root_cause: TODO: describe.
        event_id: TODO: describe.
        project_db: TODO: describe.
    """
    if root_cause.root_cause_id != -1:
        return await crud_update_event_root_cause(
            db=project_db,
            event_id=event_id,
            root_cause_id=root_cause.root_cause_id,
        )
    else:
        return await crud_update_event_root_cause(
            db=project_db,
            event_id=event_id,
            root_cause_id=None,
        )


@router.get("/event-devices")
async def get_event_devices(
    project_db: Annotated[Session, Depends(get_project_db)],
    db: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID,
):
    # First get all device IDs that have events in a single query
    """todo

    Args:
        project_db: TODO: describe.
        db: TODO: describe.
        project_id: TODO: describe.
    """
    project_name_short = get_project_name_short(project_id=project_id)
    if not project_name_short:
        raise HTTPException(status_code=404, detail="Project not found")

    device_ids_query = core_events.get_event_device_ids()
    device_ids_df = await device_ids_query.get_async(
        schema=project_name_short,
        output_type=OutputType.POLARS,
    )
    if device_ids_df is None or device_ids_df.is_empty():
        return {"unique_types": [], "unique_devices": []}
    device_ids = [
        int(row["device_id"])
        for row in device_ids_df.to_dicts()
        if row.get("device_id") is not None
    ]

    if not device_ids:
        return {"unique_types": [], "unique_devices": []}

    devices_with_types = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_ids=device_ids,
        deep=True,
    ).models()

    # Process results efficiently
    unique_type_ids = set()
    unique_type_names = {}
    unique_device_names = {}

    for device in devices_with_types:
        device_type = device.device_type
        if device_type:
            type_id = device_type.device_type_id
            unique_type_ids.add(type_id)
            unique_type_names[type_id] = device_type.name_long

            device_name = device.name_long or ""
            unique_device_names[device.device_id] = (
                f"{device_type.name_long} {device_name}".strip()
            )

    # Format response
    return {
        "unique_types": [
            {"device_type_id": device_type_id, "device_type_name": device_type_name}
            for device_type_id, device_type_name in sorted(unique_type_names.items())
        ],
        "unique_devices": [
            {"device_id": device_id, "device_name_full": device_name_full}
            for device_id, device_name_full in sorted(unique_device_names.items())
        ],
    }


@router.get("/get-events-summary", response_model=list[interfaces.EventSummary])
async def get_events_summary(
    project_db: Annotated[Session, Depends(get_project_db)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    *,
    open: bool = True,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    device_type_ids: Annotated[list[int] | None, Query()] = None,
    device_ids: Annotated[list[int] | None, Query()] = None,
    project_id: uuid.UUID | None = None,
    project: Annotated[models.Project, Depends(get_project_api)],
) -> list[interfaces.EventSummary]:
    """Generate a summary of events with associated device/failure/root-cause and
    loss info.

    Args:
        project_db: TODO: describe.
        db: TODO: describe.
        open: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        device_type_ids: TODO: describe.
        device_ids: TODO: describe.
        project_id: TODO: describe.
        project: TODO: describe.
    """

    # Time zone (same behavior: only use project's tz if project_id is provided)
    tzinfo = ZoneInfo(project.time_zone if project_id else "UTC")

    if start is not None:
        start = start.astimezone(tzinfo)
    if end is not None:
        end = end.astimezone(tzinfo)

    # Fetch events via DbQuery to avoid ORM overhead
    project_name_short = (
        get_project_name_short(project_id=project_id)
        if project_id is not None
        else project.name_short
    )
    if not project_name_short:
        raise HTTPException(status_code=404, detail="Project not found")

    events_query = core_events.get_events_summary(
        open=open,
        start=start,
        end=end,
        device_type_ids=device_type_ids,
        device_ids=device_ids,
    )
    events_df = await events_query.get_async(
        schema=project_name_short,
        output_type=OutputType.POLARS,
    )
    if events_df is None or events_df.is_empty():
        return []
    events = events_df.to_dicts()
    if not events:
        return []

    event_ids = [int(e["event_id"]) for e in events]
    failure_mode_ids = list(
        {int(e["failure_mode_id"]) for e in events if e["failure_mode_id"] is not None}
    )
    root_cause_ids = list(
        {int(e["root_cause_id"]) for e in events if e["root_cause_id"] is not None}
    )

    # Parallelize async database calls
    failure_modes_query = get_failure_modes(failure_mode_ids=failure_mode_ids)
    failure_modes_task = failure_modes_query.get_async(
        output_type=OutputType.SQLALCHEMY,
    )
    root_causes_task = get_root_causes(db=db, root_cause_ids=root_cause_ids)
    # Run loss query in parallel with other async calls
    losses_task = asyncio.to_thread(
        core.crud.project.event_losses.get_event_losses_summary_in_sql,
        project_db,
        project_name=project_name_short,
        event_ids=event_ids,
    )

    # Wait for all async operations to complete
    failure_modes, root_causes, losses = await asyncio.gather(
        failure_modes_task, root_causes_task, losses_task
    )

    failure_mode_id_to_name = {fm.failure_mode_id: fm.name_long for fm in failure_modes}
    root_cause_id_to_name = {rc.root_cause_id: rc.name_long for rc in root_causes}

    # Process losses data in thread pool (pandas operations are CPU-bound)
    def process_losses_data(
        *, losses_rows: Any, events_list: list
    ) -> dict[int, dict[str, float | None]]:
        # Convert Row objects to dicts for proper DataFrame column names
        # SQLAlchemy Row objects use _mapping attribute (2.0+) or _asdict() (older)
        """todo

        Args:
            losses_rows: TODO: describe.
            events_list: TODO: describe.
        """
        try:
            losses_dicts = [dict(row._mapping) for row in losses_rows]
        except AttributeError:
            # Fallback for older SQLAlchemy versions
            losses_dicts = [row._asdict() for row in losses_rows]
        losses_df = pd.DataFrame(losses_dicts)

        # If no losses, keep existing behavior
        if losses_df.empty:
            return {}

        # Ensure expected columns exist (SQL already aggregated)
        cols_needed = {"event_id", "time_min", "time_max", "loss_1", "loss_2"}
        missing = cols_needed - set(losses_df.columns)
        if missing:
            raise RuntimeError(f"event_losses missing columns: {missing}")

        # SQL already aggregated, so we have one row per event_id
        g = losses_df.copy()
        cols_to_mwh = ["loss_1", "loss_1_daily"]
        for col in cols_to_mwh:
            if col in g.columns:
                g[col] = g[col] / 12

        # 1) Calculate days_data_span from SQL-aggregated time_min/time_max
        g["days_data_span"] = (
            pd.to_datetime(g["time_max"]).dt.floor("D")
            - pd.to_datetime(g["time_min"]).dt.floor("D")
        ).dt.days + 1

        # 2) per event duration (event-based denominator)
        ev = pd.DataFrame(
            [
                {
                    "event_id": e["event_id"],
                    "time_start": e["time_start"],
                    "time_end": e["time_end"]
                    or datetime.datetime.now(e["time_start"].tzinfo),
                }
                for e in events_list
            ]
        )
        # Align tz and floor to whole days if you want calendar-aware durations
        ev["days_event"] = (
            ev["time_end"].dt.floor("D") - ev["time_start"].dt.floor("D")
        ).dt.days + 1

        # 3) choose denominator: event duration (matches your refactor)
        g = g.merge(ev[["event_id", "days_event"]], on="event_id", how="left")
        denom = g["days_event"]  # or g["days_data_span"] for original behavior

        # 4) Calculate daily averages from SQL-aggregated totals
        # loss_1 = energy (event_loss_type_id == EventLossType.PROXIMAL_ENERGY)
        # loss_2 = financial (event_loss_type_id == EventLossType.PROXIMAL_FINANCIAL)
        g["avg_loss_per_day_1"] = g["loss_1"] / denom.replace({0: pd.NA})
        g["avg_loss_per_day_2"] = g["loss_2"] / denom.replace({0: pd.NA})

        # 5) build losses_map in O(E)
        losses_map = {}
        for _, row in g.iterrows():
            ev_id = row["event_id"]
            losses_map[ev_id] = {
                "loss_total_energy": _none_if_nan(row.get("loss_1")),
                "loss_total_financial": _none_if_nan(row.get("loss_2")),
                "loss_daily_energy": _none_if_nan(row.get("avg_loss_per_day_1")),
                "loss_daily_financial": _none_if_nan(row.get("avg_loss_per_day_2")),
            }
        return losses_map

    losses_map = await asyncio.to_thread(
        process_losses_data, losses_rows=losses, events_list=events
    )

    unknown = "Unknown"
    out: list[interfaces.EventSummary] = []
    for e in events:
        device_type_name = e.get("device_type_name_long") or unknown
        device_name = e.get("device_name_long") or ""
        device_name_full = f"{device_type_name} {device_name}"

        event_losses = losses_map.get(e["event_id"], {})
        out.append(
            interfaces.EventSummary(
                event_id=e["event_id"],
                device_type_name=device_type_name,
                device_name_full=device_name_full,
                time_start=e["time_start"],
                time_end=e["time_end"],
                failure_mode=failure_mode_id_to_name.get(
                    e["failure_mode_id"],
                    unknown,
                ),
                root_cause=root_cause_id_to_name.get(
                    e["root_cause_id"],
                    unknown,
                ),
                loss_total_financial=event_losses.get("loss_total_financial"),
                loss_total_energy=event_losses.get("loss_total_energy"),
                loss_daily_financial=event_losses.get("loss_daily_financial"),
                loss_daily_energy=event_losses.get("loss_daily_energy"),
            )
        )

    return out


@router.get("/uptime")
async def get_uptime(
    start: datetime.datetime,
    end: datetime.datetime,
    project_db: Annotated[Session, Depends(get_project_db)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
):
    # Query events from the database
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project_db: TODO: describe.
        db: TODO: describe.
        project: TODO: describe.
    """
    events = core_events.get_windowed_events(
        db=project_db, start=start, end=end, include_underperformance=False
    ).models()

    if not events:
        return []

    if project.project_type_id != ProjectType.BESS:
        # Get POA data efficiently for daylight hours calculation
        poa_df = utils.data_df(
            project_db,
            project,
            tags=core.crud.project.tags.get_project_tags(
                db=project_db,
                sensor_type_ids=[SensorType.MET_STATION_POA],
            ).models(),
            start=start,
            end=end,
            fillna_zero=False,
            get_last=False,
        )

        # Create a set of allowed downtime timestamps (more efficient than
        # DatetimeIndex)
        allowed_timestamps = set(poa_df[poa_df > 10].mean(axis=1).dropna().index)
    else:
        allowed_timestamps = set(pd.date_range(start=start, end=end, freq="5min"))
    possible_uptime = len(allowed_timestamps) * 5 / 60  # 5 minute data to hours

    # Process events into a more efficient structure
    now = datetime.datetime.now(datetime.UTC)
    device_downtime = {}  # Dict to track downtime by device

    # Get the standard UTC timezone object to ensure consistency
    utc_tz = datetime.UTC

    for event in events:
        # Get event boundaries, clipping to window
        # Convert timestamps to use the same UTC timezone object to avoid
        # pandas timezone comparison issues
        event_start = max(event.time_start, start)
        if event_start.tzinfo is not None:
            event_start = event_start.replace(tzinfo=utc_tz)

        event_end_raw = event.time_end or now
        event_end = min(event_end_raw, end)
        if event_end.tzinfo is not None:
            event_end = event_end.replace(tzinfo=utc_tz)

        if event_start >= event_end:
            continue

        # Get all valid timestamps within the event (only those in allowed_timestamps)
        try:
            event_timestamps = pd.date_range(event_start, event_end, freq="5min")

            # Count valid downtime
            valid_timestamps = [
                ts for ts in event_timestamps if ts in allowed_timestamps
            ]
            valid_hours = len(valid_timestamps) * 5 / 60  # Convert to hours

            # Skip events with less than 10 minutes of downtime
            if valid_hours <= 1 / 6:
                continue

            # Update device downtime data
            device_id = event.device_id
            if device_id not in device_downtime:
                device_downtime[device_id] = {"hours": 0.0, "count": 0}

            device_downtime[device_id]["hours"] += valid_hours
            device_downtime[device_id]["count"] += 1
        except TypeError as e:
            # Log or handle timezone errors
            logging.error(f"Timezone error processing event {event.event_id}: {e}")
            continue

    # Fetch device and device type data in batches
    device_ids = list(device_downtime.keys())
    if not device_ids:
        return []

    devices = core.crud.project.devices.get_project_devices(
        project_db, device_ids=device_ids
    ).models()
    device_dict = {device.device_id: device for device in devices}

    device_type_ids = list(set(device.device_type_id for device in devices))
    device_types = await get_device_types(db=db, device_type_ids=device_type_ids)
    device_type_dict = {dt.device_type_id: dt for dt in device_types}

    # Prepare result
    result = []
    for device_id, data in device_downtime.items():
        device = device_dict.get(device_id)
        if not device:
            continue

        # Skip tracker_pv_pcs
        if device.device_type_id == DeviceType.TRACKER_PV_PCS:
            continue

        device_type = device_type_dict.get(device.device_type_id)
        if not device_type:
            continue

        device_name_long = device.name_long or ""
        device_type_name = device_type.name_long

        result.append(
            {
                "device_id": device_id,
                "device_type_id": device.device_type_id,
                "device_name_full": f"{device_type_name} {device_name_long}".strip(),
                "downtime_hours": min(data["hours"], possible_uptime),
                "downtime_percentage": min(data["hours"] / possible_uptime, 1),
                "events": data["count"],
            },
        )

    return result


@router.get("/event-trace-tags", response_model=list[interfaces.Tag])
def get_event_trace_tags(
    project_db: Annotated[Session, Depends(get_project_db)],
    device_id: int,
):
    """todo

    Args:
        project_db: TODO: describe.
        device_id: TODO: describe.
    """
    device = core.crud.project.devices.get_project_devices(
        project_db, device_ids=[device_id]
    ).models()[0]
    child_devices = core.crud.project.devices.get_project_devices(
        project_db,
        device_id_descendent_of=device.device_id,
    ).models()
    ancestor_devices = core.crud.project.devices.get_project_devices(
        project_db,
        device_id_path_ancestor_of=device.device_id_path,
    ).models()
    device_ids = [device_id]
    device_ids.extend([child.device_id for child in child_devices])
    device_ids.extend([ancestor.device_id for ancestor in ancestor_devices])
    match device.device_type_id:
        case 2:  # PV PCS
            sensor_type_ids = [
                2,  # PV PCS AC Power
                # 3,  # PV PCS Module AC Power
                9,  # PV PCS AC Power Setpoint
                34,  # PV PCS Module Internal Temperature
                38,  # PV PCS Module DC Voltage
                46,  # PV PCS Status
                47,  # PV PCS Module Status
            ]
        case 3:  # PV PCS Module
            sensor_type_ids = [
                2,  # PV PCS AC Power
                3,  # PV PCS Module AC Power
                9,  # PV PCS AC Power Setpoint
                34,  # PV PCS Module Internal Temperature
                38,  # PV PCS Module DC Voltage
                46,  # PV PCS Status
                47,  # PV PCS Module Status
            ]
        case 5:  # Meter
            sensor_type_ids = [
                1,  # Meter Active Power
            ]
        case 9:  # PV DC Combiner
            sensor_type_ids = [
                2,  # PV PCS AC Power
                3,  # PV PCS Module AC Power
                27,  # PV DC Combiner Current
                46,  # PV PCS Status
                47,  # PV PCS Module Status
            ]
        case 13:  # BESS PCS
            sensor_type_ids = [
                80,  # BESS PCS Available Charge Power
                81,  # BESS PCS Available Discharge Power
                137,  # BESS PCS Module Status
                140,  # BESS PCS Module Alarm
                142,  # BESS PCS Status
                143,  # BESS Bank Status
            ]
        case 26:  # BESS Bank
            sensor_type_ids = [
                44,  # BESS Bank SOC
                50,  # BESS Bank Current
                51,  # BESS Bank Voltage
                80,  # BESS PCS Available Charge Power
                81,  # BESS PCS Available Discharge Power
                137,  # BESS PCS Module Status
                140,  # BESS PCS Module Alarm
                142,  # BESS PCS Status
                143,  # BESS Bank Status
            ]
        case 27:  # BESS String
            sensor_type_ids = [
                45,  # BESS String SOC
                57,  # BESS String Current
                58,  # BESS String Voltage
                80,  # BESS PCS Available Charge Power
                81,  # BESS PCS Available Discharge Power
                137,  # BESS PCS Module Status
                140,  # BESS PCS Module Alarm
                142,  # BESS PCS Status
                143,  # BESS Bank Status
            ]
        case 28:  # Tracker Zone
            sensor_type_ids = [
                24,  # Tracker Position
                25,  # Tracker Setpoint
                48,  # Tracker Zone Status
                49,  # Tracker Row Status
            ]
        case 29:  # Tracker Row
            sensor_type_ids = [
                24,  # Tracker Position
                25,  # Tracker Setpoint
                48,  # Tracker Zone Status
                49,  # Tracker Row Status
            ]
        case 33:  # BESS PCS Module
            sensor_type_ids = [
                99,  # BESS PCS Module Available Charge Power
                100,  # BESS PCS Module Available Discharge Power
                106,  # BESS PCS Module AC Power
                108,  # BESS PCS Module Cabinet Temperature
                110,  # BESS PCS Module DC Voltage
                137,  # BESS PCS Module Status
                140,  # BESS PCS Module Alarm
            ]
        case _:
            sentry_sdk.capture_exception(
                ValueError(f"Device type {device.device_type_id} not supported.")
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    "This device type is not yet supported. The Proximal Team "
                    "has been notified."
                ),
            )
    tags = core.crud.project.tags.get_project_tags(
        db=project_db,
        device_ids=device_ids,
        sensor_type_ids=sensor_type_ids,
        deep=True,
    ).models()
    return tags


@router.get("/llm-event-losses")
async def get_llm_event_losses(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    project_db: Annotated[Session, Depends(get_project_db)],
    project_id: uuid.UUID,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """todo

    Args:
        db: Operational database
        project_db: TODO: describe.
        project_id: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    try:
        if isinstance(start, str):
            start = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
        if isinstance(end, str):
            end = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))

        project_name_short = get_project_name_short(project_id=project_id)
        if not project_name_short:
            raise HTTPException(status_code=404, detail="Project not found")

        event_data_query = core_events.get_events_with_device_info(
            time_end_gte=start,
            time_end_lt=end,
            open=False,
        )
        event_data_df = await event_data_query.get_async(
            schema=project_name_short,
            output_type=OutputType.POLARS,
        )
        if event_data_df is None or event_data_df.is_empty():
            return {"data": pd.DataFrame().to_dict("tight")}
        event_data = event_data_df.to_dicts()

        event_ids = [int(event["event_id"]) for event in event_data]
        event_losses = await core.crud.project.event_losses.get_event_losses(
            event_ids=event_ids,
            time_gte=start,
            time_lt=end,
        ).get_async(
            schema=project_name_short,
            output_type=OutputType.SQLALCHEMY,
        )

        failure_modes = await get_failure_modes().get_async(
            output_type=OutputType.SQLALCHEMY,
        )
        failure_mode_map = {fm.failure_mode_id: fm.name_long for fm in failure_modes}

        root_causes = await get_root_causes(db=db)
        root_cause_map = {rc.root_cause_id: rc.name_long for rc in root_causes}

        event_losses_dict: dict[int, list[models.EventLoss]] = {}
        for loss in event_losses:
            if loss.event_id not in event_losses_dict:
                event_losses_dict[loss.event_id] = []
            event_losses_dict[loss.event_id].append(loss)

        df = pd.DataFrame(
            [
                {
                    "event_id": d["event_id"],
                    "time_start": d["time_start"],
                    "time_end": d["time_end"],
                    "device_id": d["device_id"],
                    "failure_mode": failure_mode_map.get(
                        d["failure_mode_id"],
                        "Unknown",
                    ),
                    "root_cause": root_cause_map.get(
                        d["root_cause_id"] or -1,
                        "Unknown",
                    ),
                    "losses": event_losses_dict.get(d["event_id"], []),
                }
                for d in event_data
            ],
        )

        df = df.sort_values(by="time_start")

        df["losses"] = df["losses"].apply(
            lambda losses: [
                {
                    "time": loss.time,
                    "loss": loss.loss,
                    "event_loss_type_id": loss.event_loss_type_id,
                }
                for loss in losses
            ],
        )

        return {"data": df.to_dict("tight")}

    except Exception as e:
        error_trace = traceback.format_exc()
        logging.error(f"Error in get_llm_event_losses: {str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/bulk-create", response_model=interfaces.BulkCreateEventsResponse)
def bulk_create_events(
    project_db: Annotated[Session, Depends(get_project_db)],
    db: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID,
    payload: interfaces.BulkCreateEventsRequest,
):
    """Create events in bulk for a set of device_ids and attach a single loss row each.

    - Creates an `events` row per device with failure_mode_id default 1
      (Generic Underperformance)
    - Inserts an `event_losses` row at `time_start` with provided loss and
      event_loss_type_id
    - If event_loss_type_id=PROXIMAL_PV_DC_CAPACITY is not present in
      operational.event_loss_types, create it with name_short
      'proximal_pv_dc_capacity'.

    Args:
        project_db: TODO: describe.
        db: TODO: describe.
        project_id: TODO: describe.
        payload: TODO: describe.
    """
    # Ensure event_loss_type id exists (id 3 requested by frontend)
    loss_type_id = EventLossType.PROXIMAL_PV_DC_CAPACITY
    try:
        exists_query = select(models.EventLossType).where(
            models.EventLossType.event_loss_type_id == loss_type_id
        )
        exists = db.execute(exists_query).scalars().first()
        if not exists:
            new_type = models.EventLossType(
                event_loss_type_id=loss_type_id,
                name_short="proximal_pv_dc_capacity",  # allow: hardcoded-name-short
            )
            db.add(new_type)
            db.commit()
    except Exception:
        db.rollback()
        raise

    # Default failure mode to DC Field Underperforming (94) for drone inspection events
    DEFAULT_FAILURE_MODE_ID = 94

    # Get project name_short for schema name
    project_name_short = get_project_name_short(project_id=project_id)
    if not project_name_short:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate schema name to prevent SQL injection (alphanumeric and underscore only)
    if not project_name_short.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid project identifier")

    try:
        # Implement lock mechanism to prevent race conditions
        project_db.execute(text("SET lock_timeout = '30s'"))
        project_db.execute(text("BEGIN"))
        # Note: project_name_short is validated above to contain only safe characters
        project_db.execute(
            text(f"LOCK TABLE {project_name_short}.events IN ACCESS EXCLUSIVE MODE")  # noqa: S608
        )

        # Update sequence to ensure proper ID generation
        # Note: project_name_short is validated above to contain only safe characters
        project_db.execute(
            text(
                "SELECT setval( pg_get_serial_sequence("  # noqa: S608
                f"'{project_name_short}.events', 'event_id'), "
                f"COALESCE((SELECT MAX(event_id) FROM "
                f"{project_name_short}.events), 1), true )"
            )
        )
        project_db.execute(text("COMMIT"))

        # Map DC Combiner device_ids to their DC Field children (device_type_id
        # = DC_FIELD)
        combiner_device_ids = [item.device_id for item in payload.items]

        # Get DC Field devices that are direct children of our combiners
        dc_field_children = core.crud.project.devices.get_project_devices(
            project_db,
            device_type_ids=[DeviceType.DC_FIELD],
            parent_device_ids=[device_id for device_id in combiner_device_ids],
        ).models()

        # Create mapping from combiner_id to dc_field_id
        combiner_to_field_mapping = {
            dc_field.parent_device_id: dc_field.device_id
            for dc_field in dc_field_children
        }

        # Group items by target device_id to handle time offsets properly
        device_items: dict[int, list[interfaces.BulkEventItem]] = {}
        for item in payload.items:
            # Use DC Field device_id if available, otherwise fall back to
            # combiner device_id
            target_device_id = combiner_to_field_mapping.get(
                item.device_id, item.device_id
            )

            if target_device_id not in device_items:
                device_items[target_device_id] = []
            device_items[target_device_id].append(item)

        # Check for existing events to avoid conflicts
        target_device_ids = list(device_items.keys())
        existing_events_end = payload.time_start + datetime.timedelta(
            seconds=len(payload.items)
        )
        existing_events_query = select(models.Event).where(
            models.Event.device_id.in_(target_device_ids),
            models.Event.time_start >= payload.time_start,
            models.Event.time_start < existing_events_end,
        )
        existing_events = project_db.execute(existing_events_query).scalars().all()

        # Create a set of existing (device_id, time_start) combinations
        existing_combinations = {
            (event.device_id, event.time_start) for event in existing_events
        }

        # Create events and losses with proper event_id assignment
        created_event_ids = []
        losses_data = []
        # Track which event_id corresponds to which anomaly UUIDs
        event_to_anomalies_mapping = {}
        event_objects = []  # Collect all events for bulk insert

        for target_device_id, items in device_items.items():
            time_offset = 0
            for item in items:
                # Find the next available time_start for this device
                while True:
                    adjusted_time_start = payload.time_start + datetime.timedelta(
                        seconds=time_offset
                    )
                    if (
                        target_device_id,
                        adjusted_time_start,
                    ) not in existing_combinations:
                        break
                    time_offset += 1

                # Create event object (don't add to session yet)
                event = models.Event(
                    device_id=target_device_id,
                    failure_mode_id=DEFAULT_FAILURE_MODE_ID,
                    root_cause_id=payload.root_cause_id,
                    time_start=adjusted_time_start,
                    time_end=payload.time_end,
                    time_detected=datetime.datetime.now(datetime.UTC),
                    time_last_analyzed=None,
                    loss_total_financial=None,
                    version="manual-drone",
                )
                event_objects.append(event)

                # Store anomaly mapping for bulk update later
                if item.anomaly_uuids:
                    # We'll set the event_id after the event is created
                    event_to_anomalies_mapping[len(event_objects) - 1] = (
                        item.anomaly_uuids
                    )

                time_offset += 1

        # Add all events to session and flush to get their IDs
        for event in event_objects:
            project_db.add(event)
        project_db.flush()  # Flush once to get all event_ids

        # Now create loss data and update mappings with actual event_ids
        actual_event_mapping = {}
        loss_index = 0

        for target_device_id, items in device_items.items():
            for item in items:
                # Find the corresponding event object
                event_index = loss_index
                event = event_objects[event_index]

                # Ensure we have the event_id after flush
                if event.event_id is None:
                    raise ValueError(
                        f"Event at index {event_index} has no event_id after flush"
                    )

                created_event_ids.append(event.event_id)

                # Create loss data with correct values from the item
                loss_data = {
                    "event_id": event.event_id,
                    "time": payload.time_start,
                    "event_loss_type_id": item.event_loss_type_id,
                    "loss": item.loss,
                    "version": "manual-drone",
                }
                losses_data.append(loss_data)

                # Update anomaly mapping with actual event_id
                if event_index in event_to_anomalies_mapping:
                    actual_event_mapping[event.event_id] = event_to_anomalies_mapping[
                        event_index
                    ]

                loss_index += 1

        # Bulk update all anomalies in a single operation
        if actual_event_mapping:
            bulk_update_anomalies_with_event_ids(
                db=project_db,
                event_mapping=actual_event_mapping,
            )

        # Bulk insert losses using the most efficient approach
        if losses_data:
            # Single bulk INSERT with all data - this is the fastest approach
            stmt = insert(models.EventLoss)
            project_db.execute(stmt, losses_data)

        project_db.commit()

    except Exception as e:
        project_db.rollback()
        logging.error(f"bulk_create_events failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create events")

    return interfaces.BulkCreateEventsResponse(created_event_ids=created_event_ids)


@router.get("/{event_id}/anomalies")
def get_event_anomalies(
    project_db: Annotated[Session, Depends(get_project_db)],
    event_id: int = Path(..., description="Event ID to get anomalies for"),
):
    """Get all drone anomalies associated with a specific event.
        Anomalies are linked to events via the event_id column.

    Args:
        project_db: TODO: describe.
        event_id: TODO: describe.
    """
    try:
        anomalies = crud_get_anomalies_by_event_id(db=project_db, event_id=event_id)
        return anomalies
    except Exception as e:
        logging.error(f"Failed to get anomalies for event {event_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve anomalies for event"
        )


@router.get("/event-losses-summary")
async def get_event_losses_summary(
    project_id: uuid.UUID,
    event_id: int,
) -> dict[str, float | None]:
    """todo

    Args:
        project_id: The UUID of the project
        event_id: TODO: describe.
    """
    project_name_short = get_project_name_short(project_id=project_id)
    if not project_name_short:
        raise HTTPException(status_code=404, detail="Project not found")

    events = await core_events.get_events_by_id(
        event_ids=[event_id],
    ).get_async(
        schema=project_name_short,
        output_type=OutputType.SQLALCHEMY,
    )
    if not events:
        raise HTTPException(status_code=404, detail="Event not found")
    event = events[0]

    losses_df = await core.crud.project.event_losses.get_event_losses(
        event_ids=[event_id],
    ).get_async(
        schema=project_name_short,
        output_type=OutputType.PANDAS,
    )

    # Default output (None when data is missing)
    out: dict[str, float | None] = {
        "loss_total_energy": None,
        "loss_total_financial": None,
        "loss_daily_energy": None,
        "loss_daily_financial": None,
        "loss_capacity": None,
    }

    # If no event found, we cannot compute days_event (keep dailies as None)
    if event is None:
        return out

    # Compute days_event = floor(day_end) - floor(day_start) + 1
    # Use event.time_end or "now" in the same tz as time_start
    now_like = (
        datetime.datetime.now(event.time_start.tzinfo)
        if event.time_start.tzinfo
        else datetime.datetime.now()
    )
    time_end = event.time_end or now_like

    start_day = pd.Timestamp(event.time_start).floor("D")
    end_day = pd.Timestamp(time_end).floor("D")
    days_event: int | None = int((end_day - start_day).days) + 1
    if days_event is not None and days_event <= 0:
        days_event = None  # avoid divide-by-zero

    # If no losses, totals/dailies remain None, but capacity check still applies below
    if not losses_df.empty:
        # Totals per type
        sums = losses_df.groupby("event_loss_type_id")["loss"].sum()

        power_sum = sums.get(1)
        t_energy = (power_sum / 12) if power_sum is not None else None  # convert to MWh
        t_fin = sums.get(2)

        # Daily = totals / days_event (if available)
        d_energy = (
            (t_energy / days_event) if (t_energy is not None and days_event) else None
        )
        d_fin = (t_fin / days_event) if (t_fin is not None and days_event) else None

        out["loss_total_energy"] = _none_if_nan(t_energy)
        out["loss_total_financial"] = _none_if_nan(t_fin)
        out["loss_daily_energy"] = _none_if_nan(d_energy)
        out["loss_daily_financial"] = _none_if_nan(d_fin)

        # Capacity = latest value for type 3 (unchanged behavior)
        cap_rows = losses_df[losses_df["event_loss_type_id"] == 3]
        if not cap_rows.empty:
            cap_rows = cap_rows.sort_values("time", ascending=True)
            out["loss_capacity"] = _none_if_nan(cap_rows["loss"].iloc[-1])

    else:
        # No loss rows: only capacity could still be None here (no rows)
        pass

    return out
