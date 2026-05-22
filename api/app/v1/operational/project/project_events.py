import asyncio
import datetime
import logging
import uuid
from collections.abc import Sequence
from typing import Annotated, Any, Literal, cast

import numpy as np
import pandas as pd
import sentry_sdk
from core.crud.operational.device_types import get_device_types
from core.crud.operational.failure_modes import get_failure_modes
from core.crud.operational.root_causes import (
    get_root_causes_query as core_get_root_causes,
)
from core.crud.project import event_losses as core_event_losses
from core.crud.project import events as core_events
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.crud.project.devices import get_project_devices as crud_get_project_devices
from core.crud.project.event_losses import get_event_losses
from core.crud.project.events import get_windowed_events
from core.crud.project.tags import get_project_tags_v2
from core.db_query import OutputType
from core.enumerations import (
    DeviceTypeEnum,
    EventLossTypeEnum,
    ProjectTypeEnum,
    SensorTypeEnum,
)
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from shapely.errors import ShapelyError
from shapely.geometry import shape
from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app import interfaces, utils
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


def _none_if_nan(x: Any) -> float | None:  # no-star-syntax
    """Convert a value to float, returning None if the value is NaN or invalid.

    Args:
        x: Value to convert, can be any numeric type or NaN.
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
def _dtype_name_long(*, v: Any) -> str | None:
    return v.get("name_long") if isinstance(v, dict) else getattr(v, "name_long", None)


def _multipolygon_coordinates_bbox_center(
    *,
    coordinates: list[Any],
) -> interfaces.Point | None:
    """Axis-aligned bounding-box center of all polygon coordinates (fallback).

    Args:
        coordinates: Nested polygon coordinates to scan for longitude/latitude
            pairs.
    """
    longitudes: list[float] = []
    latitudes: list[float] = []

    def _collect_coordinates(
        *,
        node: Any,
        longitudes: list[float],
        latitudes: list[float],
    ) -> None:
        if not isinstance(node, (list, tuple)):
            return
        if (
            len(node) >= 2
            and isinstance(node[0], (int, float))
            and isinstance(node[1], (int, float))
        ):
            longitudes.append(float(node[0]))
            latitudes.append(float(node[1]))
            return
        for child in node:
            _collect_coordinates(
                node=child,
                longitudes=longitudes,
                latitudes=latitudes,
            )

    _collect_coordinates(
        node=coordinates,
        longitudes=longitudes,
        latitudes=latitudes,
    )
    if not longitudes or not latitudes:
        return None
    return interfaces.Point(
        type="Point",
        coordinates=[
            (min(longitudes) + max(longitudes)) / 2,
            (min(latitudes) + max(latitudes)) / 2,
        ],
    )


def _point_from_device_own_geometry(
    *, device: interfaces.DeviceInterface
) -> interfaces.Point | None:
    """Map point from this device's own ``point`` or ``polygon`` only.

    Args:
        device: Device row (no parent fallback).
    """
    if device.point is not None:
        return device.point
    if device.polygon is None:
        return None

    coords = device.polygon.coordinates
    try:
        geom = shape(
            {"type": device.polygon.type, "coordinates": coords},
        )
        centroid = geom.centroid
        if not centroid.is_empty:
            return interfaces.Point(
                type="Point",
                coordinates=[float(centroid.x), float(centroid.y)],
            )
    except (
        TypeError,
        ValueError,
        KeyError,
        IndexError,
        ShapelyError,
    ):
        pass
    return _multipolygon_coordinates_bbox_center(coordinates=coords)


def _get_event_location_point(
    *,
    device: interfaces.DeviceInterface | None,
    devices_by_id: dict[int, interfaces.DeviceInterface],
) -> interfaces.Point | None:
    """Resolve a representative point for an event's device.

    Uses the event device's ``point`` / ``polygon`` when present; otherwise walks
    ``parent_device_id`` using ``devices_by_id`` until a geometry is found.

    Args:
        device: Device associated with the event.
        devices_by_id: All loaded devices (expanded to include parents as needed).
    """
    if device is None:
        return None
    visited: set[int] = set()
    current: interfaces.DeviceInterface | None = device
    while current is not None:
        if current.device_id in visited:
            break
        visited.add(current.device_id)
        own = _point_from_device_own_geometry(device=current)
        if own is not None:
            return own
        pid = current.parent_device_id
        if pid is None:
            break
        current = devices_by_id.get(pid)
    return None


async def _expand_device_map_with_parents_for_missing_geometry(
    *,
    device_map: dict[int, interfaces.DeviceInterface],
    project_name_short: str,
) -> None:
    """Fetch parent devices when event devices lack point and polygon.

    Args:
        device_map: In-place map of device_id to Device; parents merged in.
        project_name_short: Project schema name for the devices query.
    """
    max_passes = 32
    for _ in range(max_passes):
        need_parent_ids: set[int] = set()
        for dev in device_map.values():
            if _point_from_device_own_geometry(device=dev) is not None:
                continue
            if dev.parent_device_id is None:
                continue
            if dev.parent_device_id not in device_map:
                need_parent_ids.add(dev.parent_device_id)
        if not need_parent_ids:
            break
        parent_df = await crud_get_project_devices(
            device_ids=list(need_parent_ids),
            deep=False,
        ).get_async(
            schema=project_name_short,
            output_type=OutputType.POLARS,
        )
        if parent_df is None or parent_df.is_empty():
            break
        added = False
        for row in parent_df.to_dicts():
            did = int(row["device_id"])
            if did not in device_map:
                device_map[did] = interfaces.DeviceInterface.model_validate(row)
                added = True
        if not added:
            break


async def _get_events_for_project(
    *,
    project_id: uuid.UUID,
    filters: interfaces.EventFilterRequest,
) -> list[interfaces.EventInterface]:
    """Retrieve events for a project with optional filters.

    Args:
        project_id: UUID of the project to retrieve events for.
        filters: Event filter request.
    """
    if filters.device_ids is not None and -1 in filters.device_ids:
        return []

    project_name_short = get_project_name_short(project_id=project_id)
    if not project_name_short:
        raise HTTPException(status_code=404, detail="Project not found")

    events_query = core_events.get_events_with_device_info(
        device_ids=filters.device_ids,
        time_end_gte=filters.time_end_gte,
        time_end_lt=filters.time_end_lt,
        open=filters.open,
        event_ids=filters.event_ids,
        open_at=filters.open_at,
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
    failure_modes_task = get_failure_modes(
        failure_mode_ids=failure_mode_ids,
    ).get_async(output_type=OutputType.PANDAS)

    root_causes_task = core_get_root_causes(
        root_cause_ids=root_cause_ids,
    ).get_async(output_type=OutputType.PANDAS)

    failure_modes_df, root_causes_df = await asyncio.gather(
        failure_modes_task, root_causes_task
    )

    device_map: dict[int, interfaces.DeviceInterface] = {}
    device_ids = [
        int(device_id)
        for device_id in events_df["device_id"].unique().to_list()
        if device_id is not None
    ]
    if device_ids:
        device_query = crud_get_project_devices(
            device_ids=device_ids,
            deep=False,
        )
        devices_df = await device_query.get_async(
            schema=project_name_short,
            output_type=OutputType.POLARS,
        )
        if devices_df is not None and not devices_df.is_empty():
            device_map = {
                int(device["device_id"]): interfaces.DeviceInterface.model_validate(
                    device
                )
                for device in devices_df.to_dicts()
            }

    # Create mappings from DataFrames
    def _fm_row_to_model(*, row: pd.Series) -> interfaces.FailureModeInterface:
        return interfaces.FailureModeInterface(
            failure_mode_id=int(row["failure_mode_id"]),
            device_type_id=int(row["device_type_id"]),
            name_short=str(row["name_short"]) if pd.notna(row["name_short"]) else "",
            name_long=str(row["name_long"]) if pd.notna(row["name_long"]) else "",
        )

    def _rc_row_to_model(*, row: pd.Series) -> interfaces.RootCauseInterface:
        return interfaces.RootCauseInterface(
            root_cause_id=int(row["root_cause_id"]),
            device_type_id=int(row["device_type_id"]),
            name_short=str(row["name_short"]) if pd.notna(row["name_short"]) else "",
            name_long=str(row["name_long"]) if pd.notna(row["name_long"]) else "",
        )

    failure_mode_map = (
        {
            int(row["failure_mode_id"]): _fm_row_to_model(row=row)
            for _, row in failure_modes_df.iterrows()
        }
        if not failure_modes_df.empty
        else {}
    )
    root_cause_map = (
        {
            int(row["root_cause_id"]): _rc_row_to_model(row=row)
            for _, row in root_causes_df.iterrows()
        }
        if not root_causes_df.empty
        else {}
    )

    # Process the results using a more efficient approach
    result: list[interfaces.EventInterface] = []
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

        result.append(interfaces.EventInterface(**event_dict))

    return result


@router.get("", response_model=list[interfaces.EventInterface])
async def get_events(
    project_id: uuid.UUID,
    device_ids: Annotated[list[int] | None, Query()] = None,
    time_end_gte: datetime.datetime | None = None,
    time_end_lt: datetime.datetime | None = None,
    open: bool = True,
    event_ids: Annotated[list[int] | None, Query()] = None,
    open_at: datetime.datetime | None = None,
) -> list[interfaces.EventInterface]:
    """Retrieve a list of events for a project with optional query filters.

    Args:
        project_id: UUID of the project to retrieve events for.
        device_ids: Filter events by device IDs.
        time_end_gte: Filter events ending at or after this datetime.
        time_end_lt: Filter events ending before this datetime.
        open: Include only open events (default True).
        event_ids: Filter to specific event IDs.
        open_at: Filter events that were open at this datetime.
    """
    return await _get_events_for_project(
        project_id=project_id,
        filters=interfaces.EventFilterRequest(
            device_ids=device_ids,
            time_end_gte=time_end_gte,
            time_end_lt=time_end_lt,
            open=open,
            event_ids=event_ids,
            open_at=open_at,
        ),
    )


@router.post(
    "/search",
    response_model=list[interfaces.EventInterface],
    operation_id="search_project_events",
)
async def search_events(
    project_id: uuid.UUID,
    filters: interfaces.EventFilterRequest,
) -> list[interfaces.EventInterface]:
    """Retrieve events for a project with filters in the request body.

    Args:
        project_id: UUID of the project to retrieve events for.
        filters: Event filters sent in the JSON request body.
    """
    return await _get_events_for_project(project_id=project_id, filters=filters)


@router.get("/paginated-events", response_model=list[interfaces.PaginatedEvent])
async def get_paginated_events_route(
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
) -> list[interfaces.PaginatedEvent]:
    """Retrieve paginated events for a project with sorting and filtering.

    Args:
        project_id: UUID of the project to retrieve events for.
        page: Page number for pagination.
        page_size: Number of events per page (default 20).
        sort_column: Column to sort by (default time_start).
        sort_direction: Sort direction, asc or desc (default desc).
        open: Include only open events (default True).
        start: Filter events starting at or after this datetime.
        end: Filter events starting before this datetime.
        device_type_ids: Filter to specific device type IDs.
        device_ids: Filter to specific device IDs.
        project_db: Project database session.
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

    root_cause_id_to_name = {}
    if root_cause_ids:
        root_causes = await core_get_root_causes(
            root_cause_ids=root_cause_ids,
        ).get_async(output_type=OutputType.POLARS)
        if root_causes is not None and not root_causes.is_empty():
            root_cause_id_to_name = dict(
                zip(root_causes["root_cause_id"], root_causes["name_long"])
            )

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
        device_type_ids=device_type_ids_only or [],
    ).get_async(output_type=OutputType.SQLALCHEMY)

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
async def update_event_root_cause_route(
    root_cause: Annotated[interfaces.RootCauseUpdate, Body()],
    event_id: Annotated[int, Path(title="The ID of the event to update")],
    project_db: AsyncSession = Depends(get_project_db_async),
):
    """Update the root cause assigned to an event.

    Args:
        root_cause: Root cause update payload containing the new root cause ID.
        event_id: ID of the event to update.
        project_db: Project database session.
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
    _project_db: Annotated[Session, Depends(get_project_db)],
    project_id: uuid.UUID,
):
    """Retrieve unique device types and devices that have associated events.

    Args:
        _project_db: Project database session.
        project_id: UUID of the project to query.
    """
    project_name_short = get_project_name_short(project_id=project_id)
    if not project_name_short:
        raise HTTPException(status_code=404, detail="Project not found")

    event_devices_df = await core_events.get_event_devices_summary().get_async(
        schema=project_name_short,
        output_type=OutputType.POLARS,
    )
    if event_devices_df is None or event_devices_df.is_empty():
        return {"unique_types": [], "unique_devices": []}

    unique_type_names: dict[int, str] = {}
    unique_device_names: dict[int, str] = {}
    for row in event_devices_df.to_dicts():
        device_type_id = row.get("device_type_id")
        if device_type_id is None:
            continue
        device_type_name = str(row.get("device_type_name") or "Unknown")
        unique_type_names[int(device_type_id)] = device_type_name

        device_id = row.get("device_id")
        if device_id is None:
            continue
        device_name = str(row.get("device_name") or "")
        unique_device_names[int(device_id)] = (
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
async def get_events_summary_route(
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
    open: bool = True,
    include_losses: bool = True,
    include_energy_losses: bool = True,
    start: Annotated[
        datetime.datetime | None,
        Depends(filter_start_datetime_or_none_to_date_access_start_time),
    ] = None,
    end: datetime.datetime | None = None,
    device_type_ids: Annotated[list[int] | None, Query()] = None,
    device_ids: Annotated[list[int] | None, Query()] = None,
    project_id: uuid.UUID | None = None,
) -> list[interfaces.EventSummary]:
    """Generate a summary of events with device, failure mode, root cause, and loss.

    Args:
        project_db: Project database session for loss queries.
        open: Include only open events (default True).
        include_losses: Include event loss aggregation in the response.
        include_energy_losses: Include energy loss aggregation from event_losses.
        start: Filter events starting at or after this datetime.
        end: Filter events starting before this datetime.
        device_type_ids: Filter to specific device type IDs.
        device_ids: Filter to specific device IDs.
        project_id: UUID of the project (optional if project is provided).
        project: Project model from dependency injection.
    """
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
    device_ids_in_events = list(
        {int(e["device_id"]) for e in events if e["device_id"] is not None}
    )

    unknown = "Unknown"

    # Parallelize async database calls
    failure_modes_task = (
        get_failure_modes(failure_mode_ids=failure_mode_ids).get_async(
            output_type=OutputType.PANDAS,
        )
        if failure_mode_ids
        else asyncio.sleep(0, result=pd.DataFrame())
    )
    root_causes_task = (
        core_get_root_causes(root_cause_ids=root_cause_ids).get_async(
            output_type=OutputType.PANDAS,
        )
        if root_cause_ids
        else asyncio.sleep(0, result=pd.DataFrame())
    )
    losses_task = (
        asyncio.to_thread(
            core_event_losses.get_event_losses_summary_in_sql,
            project_db,
            project_name=project_name_short,
            event_ids=event_ids,
        )
        if include_losses and include_energy_losses
        else asyncio.sleep(0, result=[])
    )
    devices_task = (
        crud_get_project_devices(
            device_ids=device_ids_in_events,
            deep=False,
        ).get_async(
            schema=project_name_short,
            output_type=OutputType.POLARS,
        )
        if device_ids_in_events
        else asyncio.sleep(0, result=cast(Any, None))
    )

    # Wait for all async operations to complete
    failure_modes_df, root_causes_df, losses, devices_df = await asyncio.gather(
        failure_modes_task, root_causes_task, losses_task, devices_task
    )

    device_map: dict[int, interfaces.DeviceInterface] = {}
    if devices_df is not None and not devices_df.is_empty():
        device_map = {
            int(device["device_id"]): interfaces.DeviceInterface.model_validate(device)
            for device in devices_df.to_dicts()
        }

    await _expand_device_map_with_parents_for_missing_geometry(
        device_map=device_map,
        project_name_short=project_name_short,
    )

    failure_mode_id_to_name = (
        failure_modes_df.set_index("failure_mode_id")["name_long"]
        .fillna(unknown)
        .astype(str)
        .to_dict()
        if not failure_modes_df.empty
        else {}
    )
    root_cause_id_to_name = (
        root_causes_df.set_index("root_cause_id")["name_long"]
        .fillna(unknown)
        .astype(str)
        .to_dict()
        if not root_causes_df.empty
        else {}
    )

    # Process losses data in thread pool (pandas operations are CPU-bound)
    def process_losses_data(
        *, losses_rows: Any, events_list: list
    ) -> dict[int, dict[str, float | None]]:
        """Process SQL loss rows and compute daily averages for each event.

        Args:
            losses_rows: SQLAlchemy Row objects containing aggregated loss data.
            events_list: List of event dictionaries with time_start and time_end.
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

    losses_map = (
        await asyncio.to_thread(
            process_losses_data, losses_rows=losses, events_list=events
        )
        if include_losses and include_energy_losses
        else {}
    )

    out: list[interfaces.EventSummary] = []
    for e in events:
        device_type_name = e.get("device_type_name_long") or unknown
        device_name = e.get("device_name_long") or ""
        device_name_full = f"{device_type_name} {device_name}"
        device_id = int(e["device_id"])
        location_point = _get_event_location_point(
            device=device_map.get(device_id),
            devices_by_id=device_map,
        )

        event_losses = losses_map.get(e["event_id"], {})
        loss_total_financial = (
            _none_if_nan(e.get("loss_total_financial")) if include_losses else None
        )
        loss_daily_financial = (
            _none_if_nan(e.get("loss_daily_financial")) if include_losses else None
        )
        out.append(
            interfaces.EventSummary(
                event_id=e["event_id"],
                device_id=device_id,
                device_type_id=int(e.get("device_type_id") or 0),
                device_type_name=device_type_name,
                device_name_full=device_name_full,
                location_point=location_point,
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
                loss_total_financial=loss_total_financial,
                loss_total_energy=event_losses.get("loss_total_energy"),
                loss_daily_financial=loss_daily_financial,
                loss_daily_energy=event_losses.get("loss_daily_energy"),
            )
        )

    return out


@router.get("/uptime")
async def get_uptime(
    start: datetime.datetime,
    end: datetime.datetime,
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
):
    """Calculate uptime metrics for a project based on active events.

    Args:
        start: Start of the analysis window.
        end: End of the analysis window.
        project_db: Project database session.
        project: Project model from dependency injection.
    """
    events = await core_events.get_windowed_events(
        start=start, end=end, include_underperformance=False
    ).get_async(
        schema=project.name_short,
        output_type=OutputType.PANDAS,
    )

    if events.empty:
        return []

    if project.project_type_id != ProjectTypeEnum.BESS:
        # Get POA data efficiently for daylight hours calculation
        tags_df = await get_project_tags_v2(
            sensor_type_ids=[SensorTypeEnum.MET_STATION_POA],
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
    allowed_ns = allowed.astype("int64").to_numpy()  # int64 ns since epoch

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
    start_ns = ev_start.astype("int64").to_numpy()
    end_ns = ev_end.astype("int64").to_numpy()

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
    device_types = await get_device_types(device_type_ids=device_type_ids).get_async(
        output_type=OutputType.SQLALCHEMY
    )
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
                _dtype_name_long(v=v) for v in device_type_dict.values()
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

    out["possible_uptime"] = float(possible_uptime)

    # 8) final shape (list[dict])
    out = out[
        [
            "device_id",
            "device_type_id",
            "device_name_full",
            "downtime_hours",
            "downtime_percentage",
            "possible_uptime",
            "events",
        ]
    ]
    return out.to_dict(orient="records")


@router.get("/event-trace-tags", response_model=list[interfaces.TagInterface])
async def get_event_trace_tags(
    project_db: Annotated[Session, Depends(get_project_db)],
    device_id: int,
):
    """Retrieve sensor tags relevant to event tracing for a specific device.

    Args:
        project_db: Project database session.
        device_id: ID of the device to retrieve trace tags for.
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
        case DeviceTypeEnum.PV_INVERTER:
            sensor_type_ids = [
                SensorTypeEnum.PV_INVERTER_AC_POWER,
                SensorTypeEnum.PV_INVERTER_AC_POWER_SETPOINT,
                SensorTypeEnum.PV_INVERTER_MODULE_INTERNAL_TEMPERATURE,
                SensorTypeEnum.PV_INVERTER_MODULE_DC_VOLTAGE,
                SensorTypeEnum.PV_INVERTER_STATUS,
                SensorTypeEnum.PV_INVERTER_MODULE_STATUS,
            ]
        case DeviceTypeEnum.PV_INVERTER_MODULE:
            sensor_type_ids = [
                SensorTypeEnum.PV_INVERTER_AC_POWER,
                SensorTypeEnum.PV_INVERTER_MODULE_AC_POWER,
                SensorTypeEnum.PV_INVERTER_AC_POWER_SETPOINT,
                SensorTypeEnum.PV_INVERTER_MODULE_INTERNAL_TEMPERATURE,
                SensorTypeEnum.PV_INVERTER_MODULE_DC_VOLTAGE,
                SensorTypeEnum.PV_INVERTER_STATUS,
                SensorTypeEnum.PV_INVERTER_MODULE_STATUS,
            ]
        case DeviceTypeEnum.METER:
            sensor_type_ids = [
                SensorTypeEnum.METER_ACTIVE_POWER,
            ]
        case DeviceTypeEnum.PV_DC_COMBINER:
            sensor_type_ids = [
                SensorTypeEnum.PV_INVERTER_AC_POWER,
                SensorTypeEnum.PV_INVERTER_MODULE_AC_POWER,
                SensorTypeEnum.PV_DC_COMBINER_CURRENT,
                SensorTypeEnum.PV_INVERTER_STATUS,
                SensorTypeEnum.PV_INVERTER_MODULE_STATUS,
            ]
        case DeviceTypeEnum.BESS_PCS:
            sensor_type_ids = [
                SensorTypeEnum.BESS_PCS_AVAILABLE_CHARGE_POWER,
                SensorTypeEnum.BESS_PCS_AVAILABLE_DISCHARGE_POWER,
                SensorTypeEnum.BESS_PCS_MODULE_STATUS,
                SensorTypeEnum.BESS_PCS_MODULE_ALARM,
                SensorTypeEnum.BESS_PCS_STATUS,
                SensorTypeEnum.BESS_BANK_STATUS,
            ]
        case DeviceTypeEnum.BESS_BANK:
            sensor_type_ids = [
                SensorTypeEnum.BESS_BANK_SOC_PERCENT,
                SensorTypeEnum.BESS_BANK_CURRENT,
                SensorTypeEnum.BESS_BANK_VOLTAGE,
                SensorTypeEnum.BESS_PCS_AVAILABLE_CHARGE_POWER,
                SensorTypeEnum.BESS_PCS_AVAILABLE_DISCHARGE_POWER,
                SensorTypeEnum.BESS_PCS_MODULE_STATUS,
                SensorTypeEnum.BESS_PCS_MODULE_ALARM,
                SensorTypeEnum.BESS_PCS_STATUS,
                SensorTypeEnum.BESS_BANK_STATUS,
            ]
        case DeviceTypeEnum.BESS_STRING:
            sensor_type_ids = [
                SensorTypeEnum.BESS_STRING_SOC_PERCENT,
                SensorTypeEnum.BESS_STRING_CURRENT,
                SensorTypeEnum.BESS_STRING_VOLTAGE,
                SensorTypeEnum.BESS_PCS_AVAILABLE_CHARGE_POWER,
                SensorTypeEnum.BESS_PCS_AVAILABLE_DISCHARGE_POWER,
                SensorTypeEnum.BESS_PCS_MODULE_STATUS,
                SensorTypeEnum.BESS_PCS_MODULE_ALARM,
                SensorTypeEnum.BESS_PCS_STATUS,
                SensorTypeEnum.BESS_BANK_STATUS,
            ]
        case DeviceTypeEnum.TRACKER_ZONE:
            sensor_type_ids = [
                SensorTypeEnum.TRACKER_ROW_POSITION,
                SensorTypeEnum.TRACKER_ROW_SETPOINT,
                SensorTypeEnum.TRACKER_ZONE_STATUS,
                SensorTypeEnum.TRACKER_ROW_STATUS,
            ]
        case DeviceTypeEnum.TRACKER_ROW:
            sensor_type_ids = [
                SensorTypeEnum.TRACKER_ROW_POSITION,
                SensorTypeEnum.TRACKER_ROW_SETPOINT,
                SensorTypeEnum.TRACKER_ZONE_STATUS,
                SensorTypeEnum.TRACKER_ROW_STATUS,
            ]
        case DeviceTypeEnum.BESS_PCS_MODULE:
            sensor_type_ids = [
                SensorTypeEnum.BESS_PCS_MODULE_AVAILABLE_CHARGE_POWER,
                SensorTypeEnum.BESS_PCS_MODULE_AVAILABLE_DISCHARGE_POWER,
                SensorTypeEnum.BESS_PCS_MODULE_AC_POWER,
                SensorTypeEnum.BESS_PCS_MODULE_CABINET_TEMPERATURE,
                SensorTypeEnum.BESS_PCS_MODULE_DC_VOLTAGE,
                SensorTypeEnum.BESS_PCS_MODULE_STATUS,
                SensorTypeEnum.BESS_PCS_MODULE_ALARM,
            ]
        case DeviceTypeEnum.PROJECT:
            sensor_type_ids = [
                SensorTypeEnum.METER_ACTIVE_POWER,
            ]
        case DeviceTypeEnum.PV_FEEDER:
            sensor_type_ids = [
                SensorTypeEnum.PV_INVERTER_AC_POWER,
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
    tags_df = await get_project_tags_v2(
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
    project: Annotated[models.Project, Depends(get_project_api)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """Get LLM event losses for a project.

    Args:
        project: Project
        start: Start time
        end: End time
    """

    if start is None or end is None:
        start = pd.Timestamp.now(tz=project.time_zone).normalize()
        end = start + pd.Timedelta(days=1)

    try:
        start = pd.Timestamp(start).tz_localize(project.time_zone)
        end = pd.Timestamp(end).tz_localize(project.time_zone)
    except TypeError:
        start = pd.Timestamp(start).tz_convert(project.time_zone)
        end = pd.Timestamp(end).tz_convert(project.time_zone)

    events_df = await get_windowed_events(start=start, end=end).get_async(
        output_type=OutputType.PANDAS, schema=project.name_short
    )

    failure_modes_df = await get_failure_modes(
        failure_mode_ids=events_df["failure_mode_id"].unique().tolist()
    ).get_async(output_type=OutputType.PANDAS, schema=project.name_short)
    failure_modes_dict = failure_modes_df.set_index("failure_mode_id")[
        "name_long"
    ].to_dict()

    root_causes_df = await core_get_root_causes(
        root_cause_ids=events_df["root_cause_id"].unique().tolist()
    ).get_async(output_type=OutputType.PANDAS, schema=project.name_short)
    root_causes_dict = root_causes_df.set_index("root_cause_id")["name_long"].to_dict()

    events_df["failure_mode"] = events_df["failure_mode_id"].map(failure_modes_dict)
    events_df["root_cause"] = (
        events_df["root_cause_id"].map(root_causes_dict).fillna("Unknown")
    )

    event_losses_df = await get_event_losses(
        event_ids=events_df["event_id"].unique().tolist(), time_gte=start, time_lt=end
    ).get_async(output_type=OutputType.PANDAS, schema=project.name_short)

    loss_cols = ["time", "event_loss_type_id", "loss"]
    losses_dict = (
        event_losses_df.groupby("event_id")[loss_cols]
        .apply(lambda x: x.to_dict(orient="records"))
        .to_dict()
    )
    events_df["losses"] = events_df["event_id"].map(losses_dict)

    out_df = events_df[
        [
            "event_id",
            "time_start",
            "time_end",
            "device_id",
            "failure_mode",
            "root_cause",
            "losses",
        ]
    ]

    return {"data": out_df.to_dict("tight")}


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
        project_db: Project database session for event creation.
        db: Operational database session for event loss type validation.
        project_id: UUID of the project to create events for.
        payload: Bulk event creation request containing items and metadata.
    """
    # Ensure event_loss_type id exists (id 3 requested by frontend)
    loss_type_id = EventLossTypeEnum.PROXIMAL_PV_DC_CAPACITY
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
            device_type_ids=[DeviceTypeEnum.DC_FIELD],
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
    """Retrieve all drone anomalies associated with a specific event.

    Args:
        project_db: Project database session.
        event_id: ID of the event to retrieve anomalies for.
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
    """Retrieve a summary of losses for an event including totals and daily averages.

    Args:
        project_id: UUID of the project containing the event.
        event_id: ID of the event to retrieve loss summary for.
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
async def get_5min_event_losses_route(
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
    ) -> float:  # no-star-syntax
        total = 0.0
        for series in entry.get("data", []):
            losses = series.get("losses", {})
            loss_values = losses.get("loss", [])
            if loss_values:
                total += float(sum(loss_values))
        return total

    results.sort(key=_total_loss, reverse=False)

    return results
