import asyncio
import datetime
import logging
import traceback
import uuid
from collections.abc import Sequence
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import sentry_sdk
from core.crud.operational.device_types import get_device_types
from core.crud.operational.failure_modes import get_failure_modes
from core.crud.project import event_losses as core_event_losses
from core.crud.project import events as core_events
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.crud.project.devices import get_project_devices as crud_get_project_devices
from core.db_query import OutputType
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
from app._dependencies.filtering import (
    filter_start_datetime_or_none_to_date_access_start_time,
)
from app.dependencies import (
    get_async_db,
    get_project_api,
    get_project_db,
    get_project_db_async,
    get_project_name_short,
)
from core import models

router = APIRouter(prefix="/events", tags=["project_events"])


def _none_if_nan(x: Any) -> float | None:  # nosemgrep: python-enforce-keyword-only-args
    """todo

    Args:
        x: Description for x.
    """
    if x is None:
        return None
    try:
        return None if pd.isna(x) else float(x)
    except (TypeError, ValueError):
        return None


# device types dict -> DataFrame
# device_type_dict values may be objects; handle either dict-like
# or object with attributes
def _dtype_name_long(v: Any) -> str | None:
    return v.get("name_long") if isinstance(v, dict) else getattr(v, "name_long", None)


@router.get("", response_model=list[interfaces.Event])
async def get_events(
    db: Annotated[AsyncSession, Depends(get_async_db)],
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
        db: Description for db.
        project_id: Description for project_id.
        device_id: Description for device_id.
        time_end_gte: Description for time_end_gte.
        time_end_lt: Description for time_end_lt.
        open: Description for open.
        event_ids: Description for event_ids.
        open_at: Description for open_at.
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

    device_map: dict[int, interfaces.Device] = {}
    device_ids = [
        int(device_id)
        for device_id in events_df["device_id"].unique().to_list()
        if device_id is not None
    ]
    if device_ids:
        device_query = crud_get_project_devices(
            device_ids=device_ids,
            deep=True,
        )
        devices = await device_query.get_async(
            schema=project_name_short,
            output_type=OutputType.SQLALCHEMY,
        )
        if devices:
            device_map = {
                device.device_id: interfaces.Device.model_validate(
                    device, from_attributes=True
                )
                for device in devices
            }

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

        if event_dict.get("device_id") in device_map:
            event_dict["device"] = device_map[event_dict["device_id"]]

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
        project_id: Description for project_id.
        page: Description for page.
        page_size: Description for page_size.
        sort_column: Description for sort_column.
        sort_direction: Description for sort_direction.
        open: Description for open.
        start: Description for start.
        end: Description for end.
        device_type_ids: Description for device_type_ids.
        device_ids: Description for device_ids.
        project_db: Description for project_db.
        db: Description for db.
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
        root_cause_ids=root_cause_ids or [],
    )

    root_cause_id_to_name = {rc.root_cause_id: rc.name_long for rc in root_causes}

    # Devices and types
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_df = await crud_get_project_devices(device_ids=device_ids_only).get_async(
        output_type=OutputType.PANDAS, schema=project_schema
    )
    devices_df = devices_df.copy()
    devices_df["device_id"] = devices_df["device_id"].astype(int)
    devices_df["device_type_id"] = devices_df["device_type_id"].astype(int)
    device_dict = devices_df.set_index("device_id").to_dict(orient="index")

    device_type_ids_only = devices_df["device_type_id"].dropna().astype(int).tolist()

    device_types = await get_device_types(
        db=db,
        device_type_ids=device_type_ids_only or [],
    )

    device_type_dict = {dt.device_type_id: dt for dt in device_types}

    # Precompute full device names
    device_name_full_by_event: dict[uuid.UUID, str] = {}
    for e in event_objs:
        d = device_dict.get(int(e["device_id"]))
        if d:
            dt = device_type_dict.get(d["device_type_id"])
            if dt:
                name_long = d.get("name_long")
                if pd.isna(name_long):
                    name_long = ""
                device_name_full_by_event[e["event_id"]] = f"{dt.name_long} {name_long}"

    # Losses (pivot once, NaN -> None)
    losses_df = await core_event_losses.get_event_losses(
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

        denom_nonzero = denom.astype("float64").where(denom != 0)
        g["avg_loss_per_day"] = g["total_loss"] / denom_nonzero

        # 4) pivot once
        totals = g.pivot(
            index="event_id", columns="event_loss_type_id", values="total_loss"
        )
        dailies = g.pivot(
            index="event_id", columns="event_loss_type_id", values="avg_loss_per_day"
        )

        # 5) build losses_map in O(E)
        losses_map = {}
        has = lambda frame, col: (
            (frame is not None) and (col in getattr(frame, "columns", []))
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
        root_cause: Description for root_cause.
        event_id: Description for event_id.
        project_db: Description for project_db.
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
    db: Annotated[AsyncSession, Depends(get_async_db)],
    project_id: uuid.UUID,
):
    # First get all device IDs that have events in a single query
    """todo

    Args:
        project_db: Description for project_db.
        db: Description for db.
        project_id: Description for project_id.
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

    project_schema = utils.get_project_schema(project_db=project_db)
    devices_df = await crud_get_project_devices(
        device_ids=device_ids,
        deep=False,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    device_type_ids = devices_df["device_type_id"].dropna().astype(int).tolist()
    device_types = await get_device_types(
        db=db,
        device_type_ids=device_type_ids,
    )
    device_type_names = {
        device_type.device_type_id: device_type.name_long
        for device_type in device_types
    }

    unique_type_names = {
        device_type_id: device_type_name
        for device_type_id, device_type_name in device_type_names.items()
    }
    unique_device_names = {}
    for device in devices_df.to_dict("records"):
        device_type_id = device.get("device_type_id")
        if device_type_id is None or pd.isna(device_type_id):
            continue
        device_name = device.get("name_long")
        if pd.isna(device_name):
            device_name = ""
        device_type_name = device_type_names.get(int(device_type_id))
        if not device_type_name:
            continue
        unique_device_names[int(device["device_id"])] = (
            f"{device_type_name} {device_name}".strip()
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
    start: Annotated[
        datetime.datetime | None,
        Depends(filter_start_datetime_or_none_to_date_access_start_time),
    ] = None,
    end: datetime.datetime | None = None,
    device_type_ids: Annotated[list[int] | None, Query()] = None,
    device_ids: Annotated[list[int] | None, Query()] = None,
    project_id: uuid.UUID | None = None,
    project: Annotated[models.Project, Depends(get_project_api)],
) -> list[interfaces.EventSummary]:
    """Generate a summary of events with associated device/failure/root-cause and
    loss info.

    Args:
        project_db: Description for project_db.
        db: Description for db.
        open: Description for open.
        start: Description for start.
        end: Description for end.
        device_type_ids: Description for device_type_ids.
        device_ids: Description for device_ids.
        project_id: Description for project_id.
        project: Description for project.
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
        core_event_losses.get_event_losses_summary_in_sql,
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
            losses_rows: Description for losses_rows.
            events_list: Description for events_list.
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
        denom_nonzero = denom.astype("float64").where(denom != 0)
        g["avg_loss_per_day_1"] = g["loss_1"] / denom_nonzero
        g["avg_loss_per_day_2"] = g["loss_2"] / denom_nonzero

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
    """Calculate uptime metrics for a project based on
    active Events within an analysis window.

    Args:
        start: The start of the analysis window.
        end: The end of the analysis window.
        project_db: The project database session.
        db: The database session.
        project: The project model.
    """
    events = await core_events.get_windowed_events(
        start=start, end=end, include_underperformance=False
    ).get_async(
        schema=project.name_short,
        output_type=OutputType.PANDAS,
    )

    if events.empty:
        return []

    if project.project_type_id != ProjectType.BESS:
        # Get POA data efficiently for daylight hours calculation
        tags_df = await core.crud.project.tags.get_project_tags_v2(
            sensor_type_ids=[SensorType.MET_STATION_POA],
        ).get_async(
            schema=project.name_short,
            output_type=OutputType.POLARS,
        )
        if tags_df is None or tags_df.is_empty():
            return []

        data_timeseries_instance = await DataTimeseries(
            project_name_short=project.name_short,
            filter_method=FilterMethod.TAG_POLARS,
            filter_values=tags_df,
            query_start=start,
            query_end=end,
            project_db=project_db,
        ).get()

        poa_df = data_timeseries_instance.df.to_pandas()
        poa_df = poa_df.set_index("time")
        poa_df.index = pd.to_datetime(poa_df.index).tz_convert(project.time_zone)
        poa_df.columns = poa_df.columns.astype(int)

        # Create a set of allowed downtime timestamps (more efficient than
        # DatetimeIndex)
        allowed_timestamps = set(poa_df[poa_df > 10].mean(axis=1).dropna().index)
    else:
        allowed_timestamps = set(pd.date_range(start=start, end=end, freq="5min"))
    possible_uptime = len(allowed_timestamps) * 5 / 60  # 5 minute data to hours

    # Process events into a more efficient structure
    now = datetime.datetime.now(datetime.UTC)
    device_downtime = {}  # Dict to track downtime by device

    step_ns = pd.Timedelta("5min").value
    # --- Normalize allowed_timestamps once ---
    allowed = pd.DatetimeIndex(sorted(allowed_timestamps))
    # pd.to_datetime(..., utc=True) converts tz-aware to UTC
    # and localizes tz-naive as UTC.
    allowed = pd.to_datetime(allowed, utc=True)
    allowed = allowed.sort_values()
    allowed_ns = allowed.view("i8")  # int64 ns since epoch (sorted)

    # --- Vectorize event window clipping & tz normalization ---
    ev = events.copy()

    # Convert to UTC consistently (handles tz-aware & tz-naive)
    ev["time_start"] = pd.to_datetime(ev["time_start"], utc=True)
    ev["time_end"] = pd.to_datetime(ev["time_end"], utc=True)

    start_utc = pd.to_datetime(start, utc=True)
    end_utc = pd.to_datetime(end, utc=True)
    now_utc = pd.to_datetime(now, utc=True)

    # Fill open-ended events with "now", then clip to [start, end]
    ev_end_raw = ev["time_end"].fillna(now_utc)
    ev_start = ev["time_start"].where(ev["time_start"] > start_utc, start_utc)
    ev_end = ev_end_raw.where(ev_end_raw < end_utc, end_utc)

    # Drop invalid/empty windows
    valid_window = ev_start < ev_end
    ev = ev.loc[valid_window].copy()
    ev_start = ev_start.loc[valid_window]
    ev_end = ev_end.loc[valid_window]

    # --- Match date_range(freq="5min") semantics (inclusive endpoints if aligned) ---
    # date_range(start, end, freq="5min") produces timestamps on the 5-min grid:
    # >= start and <= end (when end aligns).
    start_ns = ev_start.view("i8")
    end_ns = ev_end.view("i8")

    # Ceil start to next 5-min tick (unless already aligned)
    start_aligned = ((start_ns + (step_ns - 1)) // step_ns) * step_ns
    # Floor end to prior 5-min tick (unless already aligned)
    end_aligned = (end_ns // step_ns) * step_ns

    non_empty = start_aligned <= end_aligned
    ev = ev.loc[non_empty].copy()
    start_aligned = start_aligned[non_empty]
    end_aligned = end_aligned[non_empty]

    # --- Count allowed timestamps in [start_aligned, end_aligned] per event ---
    left = np.searchsorted(allowed_ns, start_aligned, side="left")
    right = np.searchsorted(allowed_ns, end_aligned, side="right")  # inclusive
    n_valid = (right - left).astype(np.int64)

    valid_hours = n_valid * (5.0 / 60.0)

    # Skip events with <= 10 minutes (<= 1/6 hour)
    keep = valid_hours > (1.0 / 6.0)
    ev = ev.loc[keep].copy()
    valid_hours = valid_hours[keep]

    # --- Aggregate per device ---
    ev["valid_hours"] = valid_hours
    agg = ev.groupby("device_id", sort=False).agg(
        hours=("valid_hours", "sum"),
        count=("valid_hours", "size"),
    )

    # Convert to your original dict structure
    device_downtime = {
        device_id: {"hours": float(row["hours"]), "count": int(row["count"])}
        for device_id, row in agg.iterrows()
    }

    # Fetch device and device type data in batches
    device_ids = [int(device_id) for device_id in device_downtime.keys()]
    if not device_ids:
        return []

    project_schema = utils.get_project_schema(project_db=project_db)
    devices_df = await crud_get_project_devices(device_ids=device_ids).get_async(
        output_type=OutputType.PANDAS, schema=project_schema
    )
    devices_df = devices_df.copy()
    devices_df["device_id"] = devices_df["device_id"].astype(int)
    devices_df["device_type_id"] = devices_df["device_type_id"].astype(int)
    device_dict = devices_df.set_index("device_id").to_dict(orient="index")

    device_type_ids = list(set(devices_df["device_type_id"].tolist()))
    device_types = await get_device_types(db=db, device_type_ids=device_type_ids)
    device_type_dict = {dt.device_type_id: dt for dt in device_types}

    # Prepare result
    # 1) downtime dict -> DataFrame
    dt = (
        pd.DataFrame.from_dict(device_downtime, orient="index")
        .rename_axis("device_id")
        .reset_index()
        .rename(columns={"hours": "downtime_hours_raw", "count": "events"})
    )

    if dt.empty:
        return []

    # 2) devices dict -> DataFrame (must include device_id + device_type_id + name_long)
    dev = pd.DataFrame.from_dict(device_dict, orient="index")
    dev = dev.reset_index().rename(columns={"index": "device_id"})
    # Ensure the key column name matches (sometimes it's already "device_id")
    if "device_id" not in dev.columns:
        dev = dev.rename(columns={dev.columns[0]: "device_id"})

    dtypes = pd.DataFrame(
        {
            "device_type_id": list(device_type_dict.keys()),
            "device_type_name_long": [
                _dtype_name_long(v) for v in device_type_dict.values()
            ],
        }
    )

    # 4) join everything
    out = dt.merge(
        dev[["device_id", "device_type_id", "name_long"]], on="device_id", how="left"
    ).merge(dtypes, on="device_type_id", how="left")

    # 5) drop missing device / missing device type
    out = out.dropna(subset=["device_type_id", "device_type_name_long"])

    # 7) build strings + metrics
    name_long = out["name_long"].fillna("")
    # If name_long can be NaN floats / pd.NA, fillna handles it; also strip whitespace
    out["device_name_full"] = (
        out["device_type_name_long"].astype(str) + " " + name_long.astype(str)
    ).str.strip()

    # Cap hours at possible_uptime and percentage at 1.0
    out["downtime_hours"] = np.minimum(
        out["downtime_hours_raw"].to_numpy(dtype=float), float(possible_uptime)
    )
    if possible_uptime > 0:
        out["downtime_percentage"] = np.minimum(
            out["downtime_hours_raw"].to_numpy(dtype=float) / float(possible_uptime),
            1.0,
        )
    else:
        out["downtime_percentage"] = 0.0

    # 8) final shape (list[dict])
    out = out[
        [
            "device_id",
            "device_type_id",
            "device_name_full",
            "downtime_hours",
            "downtime_percentage",
            "events",
        ]
    ]
    return out.to_dict(orient="records")


@router.get("/event-trace-tags", response_model=list[interfaces.Tag])
async def get_event_trace_tags(
    project_db: Annotated[Session, Depends(get_project_db)],
    device_id: int,
):
    """todo

    Args:
        project_db: Description for project_db.
        device_id: Description for device_id.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    device_df = await crud_get_project_devices(device_ids=[device_id]).get_async(
        output_type=OutputType.PANDAS, schema=project_schema
    )
    device = device_df.to_dict("records")[0]
    child_devices_df = await crud_get_project_devices(
        device_id_descendent_of=int(device["device_id"]),
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    ancestor_devices_df = await crud_get_project_devices(
        device_id_path_ancestor_of=device.get("device_id_path"),
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    device_ids = [device_id]
    device_ids.extend(child_devices_df["device_id"].astype(int).tolist())
    device_ids.extend(ancestor_devices_df["device_id"].astype(int).tolist())
    match int(device["device_type_id"]):
        case DeviceType.PV_PCS:
            sensor_type_ids = [
                SensorType.PV_PCS_AC_POWER,
                SensorType.PV_PCS_AC_POWER_SETPOINT,
                SensorType.PV_PCS_MODULE_INTERNAL_TEMPERATURE,
                SensorType.PV_PCS_MODULE_DC_VOLTAGE,
                SensorType.PV_PCS_STATUS,
                SensorType.PV_PCS_MODULE_STATUS,
            ]
        case DeviceType.PV_PCS_MODULE:
            sensor_type_ids = [
                SensorType.PV_PCS_AC_POWER,
                SensorType.PV_PCS_MODULE_AC_POWER,
                SensorType.PV_PCS_AC_POWER_SETPOINT,
                SensorType.PV_PCS_MODULE_INTERNAL_TEMPERATURE,
                SensorType.PV_PCS_MODULE_DC_VOLTAGE,
                SensorType.PV_PCS_STATUS,
                SensorType.PV_PCS_MODULE_STATUS,
            ]
        case DeviceType.METER:
            sensor_type_ids = [
                SensorType.METER_ACTIVE_POWER,
            ]
        case DeviceType.PV_DC_COMBINER:
            sensor_type_ids = [
                SensorType.PV_PCS_AC_POWER,
                SensorType.PV_PCS_MODULE_AC_POWER,
                SensorType.PV_DC_COMBINER_CURRENT,
                SensorType.PV_PCS_STATUS,
                SensorType.PV_PCS_MODULE_STATUS,
            ]
        case DeviceType.BESS_PCS:
            sensor_type_ids = [
                SensorType.BESS_PCS_AVAILABLE_CHARGE_POWER,
                SensorType.BESS_PCS_AVAILABLE_DISCHARGE_POWER,
                SensorType.BESS_PCS_MODULE_STATUS,
                SensorType.BESS_PCS_MODULE_ALARM,
                SensorType.BESS_PCS_STATUS,
                SensorType.BESS_BANK_STATUS,
            ]
        case DeviceType.BESS_BANK:
            sensor_type_ids = [
                SensorType.BESS_BANK_SOC_PERCENT,
                SensorType.BESS_BANK_CURRENT,
                SensorType.BESS_BANK_VOLTAGE,
                SensorType.BESS_PCS_AVAILABLE_CHARGE_POWER,
                SensorType.BESS_PCS_AVAILABLE_DISCHARGE_POWER,
                SensorType.BESS_PCS_MODULE_STATUS,
                SensorType.BESS_PCS_MODULE_ALARM,
                SensorType.BESS_PCS_STATUS,
                SensorType.BESS_BANK_STATUS,
            ]
        case DeviceType.BESS_STRING:
            sensor_type_ids = [
                SensorType.BESS_STRING_SOC_PERCENT,
                SensorType.BESS_STRING_CURRENT,
                SensorType.BESS_STRING_VOLTAGE,
                SensorType.BESS_PCS_AVAILABLE_CHARGE_POWER,
                SensorType.BESS_PCS_AVAILABLE_DISCHARGE_POWER,
                SensorType.BESS_PCS_MODULE_STATUS,
                SensorType.BESS_PCS_MODULE_ALARM,
                SensorType.BESS_PCS_STATUS,
                SensorType.BESS_BANK_STATUS,
            ]
        case DeviceType.TRACKER_ZONE:
            sensor_type_ids = [
                SensorType.TRACKER_POSITION,
                SensorType.TRACKER_SETPOINT,
                SensorType.TRACKER_ZONE_STATUS,
                SensorType.TRACKER_ROW_STATUS,
            ]
        case DeviceType.TRACKER_ROW:
            sensor_type_ids = [
                SensorType.TRACKER_POSITION,
                SensorType.TRACKER_SETPOINT,
                SensorType.TRACKER_ZONE_STATUS,
                SensorType.TRACKER_ROW_STATUS,
            ]
        case DeviceType.BESS_PCS_MODULE:
            sensor_type_ids = [
                SensorType.BESS_PCS_MODULE_AVAILABLE_CHARGE_POWER,
                SensorType.BESS_PCS_MODULE_AVAILABLE_DISCHARGE_POWER,
                SensorType.BESS_PCS_MODULE_AC_POWER,
                SensorType.BESS_PCS_MODULE_CABINET_TEMPERATURE,
                SensorType.BESS_PCS_MODULE_DC_VOLTAGE,
                SensorType.BESS_PCS_MODULE_STATUS,
                SensorType.BESS_PCS_MODULE_ALARM,
            ]
        case _:
            sentry_sdk.capture_exception(
                ValueError(f"Device type {device['device_type_id']} not supported.")
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    "This device type is not yet supported. The Proximal Team "
                    "has been notified."
                ),
            )
    tags_df = await core.crud.project.tags.get_project_tags_v2(
        device_ids=device_ids,
        sensor_type_ids=sensor_type_ids,
        deep=True,
    ).get_async(
        schema=project_schema,
        output_type=OutputType.PANDAS,
    )
    if tags_df is None:
        return []
    return tags_df.replace(np.nan, None).to_dict("records")


@router.get("/llm-event-losses")
async def get_llm_event_losses(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    project_id: uuid.UUID,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """todo

    Args:
        db: Operational database
        project_id: Description for project_id.
        start: Description for start.
        end: Description for end.
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
        event_losses = await core_event_losses.get_event_losses(
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
async def bulk_create_events(
    project_db: Annotated[AsyncSession, Depends(get_project_db_async)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
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
        project_db: Description for project_db.
        db: Description for db.
        project_id: Description for project_id.
        payload: Description for payload.
    """
    # Ensure event_loss_type id exists (id 3 requested by frontend)
    loss_type_id = EventLossType.PROXIMAL_PV_DC_CAPACITY
    try:
        exists_query = select(models.EventLossType).where(
            models.EventLossType.event_loss_type_id == loss_type_id
        )
        result_loss_type = await db.execute(exists_query)
        exists_loss_type = result_loss_type.scalars().first()
        if not exists_loss_type:
            new_type = models.EventLossType(
                event_loss_type_id=loss_type_id,
                name_short="proximal_pv_dc_capacity",  # allow: hardcoded-name-short
            )
            db.add(new_type)
            await db.commit()
    except Exception:
        await db.rollback()
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
        await project_db.execute(text("SET lock_timeout = '30s'"))
        await project_db.execute(text("BEGIN"))
        # Note: project_name_short is validated above to contain only safe characters
        await project_db.execute(
            text(f"LOCK TABLE {project_name_short}.events IN ACCESS EXCLUSIVE MODE")  # noqa: S608
        )

        # Update sequence to ensure proper ID generation
        # Note: project_name_short is validated above to contain only safe characters
        await project_db.execute(
            text(
                "SELECT setval( pg_get_serial_sequence("  # noqa: S608
                f"'{project_name_short}.events', 'event_id'), "
                f"COALESCE((SELECT MAX(event_id) FROM "
                f"{project_name_short}.events), 1), true )"
            )
        )
        await project_db.execute(text("COMMIT"))

        # Map DC Combiner device_ids to their DC Field children (device_type_id
        # = DC_FIELD)
        combiner_device_ids = [item.device_id for item in payload.items]

        # Get DC Field devices that are direct children of our combiners
        project_schema = await utils.get_project_schema_async(project_db=project_db)
        dc_field_children_df = await crud_get_project_devices(
            device_type_ids=[DeviceType.DC_FIELD],
            parent_device_ids=[device_id for device_id in combiner_device_ids],
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

        # Create mapping from combiner_id to dc_field_id
        combiner_to_field_mapping = {}
        for dc_field in dc_field_children_df.to_dict("records"):
            parent_device_id = dc_field.get("parent_device_id")
            if parent_device_id is None or pd.isna(parent_device_id):
                continue
            combiner_to_field_mapping[int(parent_device_id)] = int(
                dc_field["device_id"]
            )

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
        event_result = await project_db.execute(existing_events_query)
        existing_events: Sequence[models.Event] = event_result.scalars().all()

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
        await project_db.flush()  # Flush once to get all event_ids

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
            await bulk_update_anomalies_with_event_ids(
                db=project_db,
                event_mapping=actual_event_mapping,
            )

        # Bulk insert losses using the most efficient approach
        if losses_data:
            # Single bulk INSERT with all data - this is the fastest approach
            stmt = insert(models.EventLoss)
            await project_db.execute(stmt, losses_data)

        await project_db.commit()

    except Exception as e:
        await project_db.rollback()
        logging.error(f"bulk_create_events failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create events")

    return interfaces.BulkCreateEventsResponse(created_event_ids=created_event_ids)


@router.get("/{event_id}/anomalies")
async def get_event_anomalies(
    project_db: Annotated[AsyncSession, Depends(get_project_db_async)],
    event_id: int = Path(..., description="Event ID to get anomalies for"),
):
    """Get all drone anomalies associated with a specific event.
        Anomalies are linked to events via the event_id column.

    Args:
        project_db: Description for project_db.
        event_id: Description for event_id.
    """
    try:
        anomalies = await crud_get_anomalies_by_event_id(
            db=project_db, event_id=event_id
        )
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
        event_id: Description for event_id.
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

    losses_df = await core_event_losses.get_event_losses(
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


@router.get("/5min-event-losses")
async def get_5min_event_losses(
    project: Annotated[models.Project, Depends(get_project_api)],
    start: datetime.datetime,
    end: datetime.datetime,
    event_loss_type_ids: Annotated[list[int] | None, Query()] = None,
    device_ids: Annotated[list[int] | None, Query()] = None,
    aggregation_column: Annotated[
        Literal["device_id", "device_type_id", "failure_mode_id", "root_cause_id"]
        | None,
        Query(),
    ] = None,
):
    """Get 5-minute event losses for a project."""
    losses_query = core_event_losses.get_5min_event_losses(
        start=start,
        end=end,
        event_loss_type_ids=event_loss_type_ids,
        aggregation_column=aggregation_column,
        device_ids=device_ids,
    )
    losses_df = await losses_query.get_async(
        schema=project.name_short,
        output_type=OutputType.PANDAS,
    )
    if losses_df.empty:
        return []
    try:
        losses_df["time"] = pd.to_datetime(losses_df["time"]).dt.tz_convert(
            project.time_zone
        )
    except Exception:
        losses_df["time"] = pd.to_datetime(losses_df["time"]).dt.tz_localize(
            project.time_zone
        )

    if aggregation_column is None:
        # Ungrouped response
        data = [
            {
                "event_loss_type_id": int(loss_type_id),
                "losses": {
                    "time": group["time"].tolist(),
                    "loss": group["total_loss"].tolist(),
                },
            }
            for loss_type_id, group in losses_df.groupby("event_loss_type_id")
        ]
        return data

    result = []
    for group_key, group_df in losses_df.groupby(aggregation_column):
        # The database query does not sort by time when aggregation is used,
        # so we sort here.
        group_df = group_df.sort_values("time")
        data = [
            {
                "event_loss_type_id": int(loss_type_id),
                "losses": {
                    "time": loss_type_df["time"].tolist(),
                    "loss": loss_type_df["total_loss"].tolist(),
                },
            }
            for loss_type_id, loss_type_df in group_df.groupby("event_loss_type_id")
        ]
        result.append(
            {
                aggregation_column: group_key,
                "data": data,
            }
        )

    return result


@router.get("/5min-event-losses-single")
async def get_5min_event_losses_single(
    project: Annotated[models.Project, Depends(get_project_api)],
    start: datetime.datetime,
    end: datetime.datetime,
    device_id: int,
    event_loss_type_ids: Annotated[list[int] | None, Query()] = None,
):
    """Return 5-minute losses aggregated for a device and its descendants."""

    descendants_query = crud_get_project_devices(
        device_id_descendent_of=device_id,
        include_name_long=False,
    )
    descendants_df = await descendants_query.get_async(
        schema=project.name_short,
        output_type=OutputType.PANDAS,
    )

    if descendants_df is None or descendants_df.empty:
        return []

    descendants_df = descendants_df.copy()
    descendants_df["device_id"] = descendants_df["device_id"].astype(int)
    descendants_df["parent_device_id"] = descendants_df["parent_device_id"].astype(int)

    direct_children = descendants_df[descendants_df["parent_device_id"] == device_id][
        "device_id"
    ].astype(int)

    group_device_ids: dict[int, list[int]] = {
        device_id: [device_id],
    }
    for child_id in direct_children:
        pattern = rf"(?:^|\.){child_id}(?:\.|$)"
        child_descendants = (
            descendants_df[
                descendants_df["device_id_path"]
                .astype(str)
                .str.contains(pattern, regex=True, na=False)
            ]["device_id"]
            .astype(int)
            .drop_duplicates()
            .tolist()
        )
        if child_id not in child_descendants:
            child_descendants.insert(0, int(child_id))
        group_device_ids[child_id] = child_descendants

    results: list[dict[str, Any]] = []
    for group_key, devices_in_group in group_device_ids.items():
        losses_query = core_event_losses.get_5min_event_losses(
            start=start,
            end=end,
            event_loss_type_ids=event_loss_type_ids,
            device_ids=devices_in_group,
            aggregation_column=None,
        )
        losses_df = await losses_query.get_async(
            schema=project.name_short,
            output_type=OutputType.PANDAS,
        )
        if losses_df.empty:
            continue
        try:
            losses_df["time"] = pd.to_datetime(losses_df["time"]).dt.tz_convert(
                project.time_zone
            )
        except Exception:
            losses_df["time"] = pd.to_datetime(losses_df["time"]).dt.tz_localize(
                project.time_zone
            )

        grouped: dict[int, dict[str, list[Any]]] = {}
        for record in losses_df.to_dict("records"):
            loss_type_id = int(record["event_loss_type_id"])
            grouped.setdefault(loss_type_id, {"time": [], "loss": []})
            grouped[loss_type_id]["time"].append(record["time"])
            grouped[loss_type_id]["loss"].append(record["total_loss"])

        results.append(
            {
                "device_id": group_key,
                "data": [
                    {
                        "event_loss_type_id": loss_type_id,
                        "losses": losses,
                    }
                    for loss_type_id, losses in grouped.items()
                ],
            }
        )

    # Order results by sum of losses
    def _total_loss(
        entry: dict[str, Any],
    ) -> float:  # nosemgrep: python-enforce-keyword-only-args
        total = 0.0
        for series in entry.get("data", []):
            losses = series.get("losses", {})
            loss_values = losses.get("loss", [])
            if loss_values:
                total += float(sum(loss_values))
        return total

    results.sort(key=_total_loss, reverse=False)

    return results
