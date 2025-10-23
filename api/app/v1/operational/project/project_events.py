import datetime
import logging
import traceback
import uuid
from typing import Annotated, Any
from zoneinfo import ZoneInfo

import pandas as pd
import sentry_sdk
from core.crud.operational.device_types import get_device_types
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import interfaces, utils
from app._crud.operational.failure_modes import get_failure_modes, get_root_causes
from app._crud.operational.failure_modes import (
    update_event_failure_mode as crud_update_event_failure_mode,
)
from app._crud.operational.failure_modes import (
    update_event_root_cause as crud_update_event_root_cause,
)
from app._crud.projects.drone_anomalies import bulk_update_anomalies_with_event_ids
from app._crud.projects.drone_anomalies import (
    get_anomalies_by_event_id as crud_get_anomalies_by_event_id,
)
from app._crud.projects.events import get_count_open as crud_get_count_open
from app._crud.projects.events import get_event_device_ids as crud_get_event_device_ids
from app._crud.projects.events import get_events_summary as crud_get_events_summary
from app._crud.projects.events import (
    get_events_with_device_info as crud_get_events_with_device_info,
)
from app._crud.projects.events import get_paginated_events as crud_get_paginated_events
from app.dependencies import (
    get_async_db,
    get_db,
    get_project,
    get_project_db,
    get_project_db_async,
    get_project_name_short,
)
from core import models

router = APIRouter(prefix="/projects/{project_id}/events", tags=["project_events"])


@router.get("/", response_model=list[interfaces.Event])
def get_events(
    db: Annotated[Session, Depends(get_db)],
    project_db: Annotated[Session, Depends(get_project_db)],
    device_id: int | None = None,
    time_end_gte: datetime.datetime | None = None,
    time_end_lt: datetime.datetime | None = None,
    open: bool = True,
    event_ids: Annotated[list[int] | None, Query()] = None,
    open_at: datetime.datetime | None = None,
):
    if device_id == -1:
        return None

    # Use the CRUD function to get events with device information
    events = crud_get_events_with_device_info(
        project_db,
        device_id=device_id,
        time_end_gte=time_end_gte,
        time_end_lt=time_end_lt,
        open=open,
        event_ids=event_ids,
        open_at=open_at,
    )

    if len(events) == 0:
        return []

    # Process the results using a more efficient approach
    result = []
    for event in events:
        device = event.device
        device_type = device.device_type if device else None

        device_type_name = device_type.name_long if device_type else "Unknown"
        device_name = device.name_long or ""
        device_name_full = f"{device_type_name} {device_name}"

        event_dict = event.__dict__.copy()
        if "_sa_instance_state" in event_dict:
            del event_dict["_sa_instance_state"]

        event_dict["device_name_full"] = device_name_full
        result.append(event_dict)

    return result


@router.get("/paginated-events", response_model=list[interfaces.PaginatedEvent])
async def get_paginated_events(
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
):
    # Get paginated events with single query
    data = crud_get_paginated_events(
        project_db,
        page=page,
        page_size=page_size,
        sort_column=sort_column,
        sort_direction=sort_direction,
        open=open,
        device_type_id=device_type_ids,
        device_ids=device_ids,
        start=start,
        end=end,
    )

    if not data:
        return []

    # Extract event_ids for all needed lookups
    if sort_column == "loss_daily":
        event_objs = [x[0] for x in data]
    else:
        event_objs = data

    event_ids = [event.event_id for event in event_objs]
    device_ids = [event.device_id for event in event_objs]

    # Batch fetch all required data in a minimal number of queries

    # 1. Get all root causes in a single query
    root_causes = await get_root_causes(db=db)
    root_cause_id_to_name = {
        root_cause.root_cause_id: root_cause.name_long for root_cause in root_causes
    }

    # 2. Get all devices in a single query
    devices = core.crud.project.devices.get_project_devices(
        project_db, device_ids=device_ids
    ).models()
    device_dict = {device.device_id: device for device in devices}

    # 3. Get all device types in a single query
    device_type_ids = list(set(device.device_type_id for device in devices))
    device_types = await get_device_types(db=db, device_type_ids=device_type_ids)
    device_type_dict = {
        device_type.device_type_id: device_type for device_type in device_types
    }

    # 4. Get all event losses in a single query
    losses = core.crud.project.event_losses.get_event_losses(
        project_db, event_ids=event_ids
    ).models()

    # Process losses data more efficiently
    loss_objects_by_event: dict[int, list] = {}
    energy_losses_by_event: dict[int, float] = {}
    financial_losses_by_event: dict[int, float] = {}

    for loss in losses:
        event_id = loss.event_id
        if event_id not in loss_objects_by_event:
            loss_objects_by_event[event_id] = []
            energy_losses_by_event[event_id] = 0.0
            financial_losses_by_event[event_id] = 0.0

        loss_objects_by_event[event_id].append(loss)

        if loss.event_loss_type_id == 1:  # Energy loss
            energy_losses_by_event[event_id] += loss.loss
        elif loss.event_loss_type_id == 2:  # Financial loss
            financial_losses_by_event[event_id] += loss.loss

    # Prepare device name lookup
    event_device_name_full_dict = {}
    for event in event_objs:
        device = device_dict.get(event.device_id)
        if device:
            device_type = device_type_dict.get(device.device_type_id)
            if device_type:
                name = f"{device_type.name_long} {device.name_long or ''}"
                event_device_name_full_dict[event.event_id] = name

    # Create summaries more efficiently
    summary_events = []
    for event in event_objs:
        event_id = event.event_id
        event_losses = loss_objects_by_event.get(event_id, [])
        num_losses = len(event_losses)

        # Calculate daily averages only if we have losses
        if num_losses > 0:
            daily_energy = (
                energy_losses_by_event.get(event_id, 0) / (num_losses / 2)
                if num_losses > 0
                else 0
            )
            daily_financial = (
                financial_losses_by_event.get(event_id, 0) / (num_losses / 2)
                if num_losses > 0
                else 0
            )
        else:
            daily_energy = 0
            daily_financial = 0

        summary_events.append(
            interfaces.PaginatedEvent(
                event_id=event_id,
                device_name_full=event_device_name_full_dict.get(event_id, "Unknown"),
                time_start=event.time_start,
                time_end=event.time_end,
                loss_daily_power=daily_energy,
                loss_today_power=0,  # This is always 0 in the original code
                loss_total_power=energy_losses_by_event.get(event_id, 0),
                loss_daily_financial=daily_financial,
                loss_today_financial=0,  # This is always 0 in the original code
                loss_total_financial=financial_losses_by_event.get(event_id, 0),
                root_cause=root_cause_id_to_name.get(event.root_cause_id) or "Unknown",
            ),
        )

    return summary_events


@router.get("/event-losses")
def get_event_losses(
    project_db: Annotated[Session, Depends(get_project_db)],
    time_equals: datetime.datetime | None = None,
    time_gte: datetime.datetime | None = None,
    time_lt: datetime.datetime | None = None,
    event_ids: Annotated[list | None, Query()] = None,
):
    """Get event losses with optimized query parameters.

    This function uses a single database query with all filters applied at once
    to minimize database round trips.
    """
    return core.crud.project.event_losses.get_event_losses(
        project_db,
        time_equals=time_equals,
        time_gte=time_gte,
        time_lt=time_lt,
        event_ids=event_ids,
    ).models()


@router.put("/{event_id}/failure-mode")
async def update_event_failure_mode(
    failure_mode: Annotated[interfaces.FailureModeUpdate, Body()],
    event_id: Annotated[int, Path(title="The ID of the event to update")],
    project_db: AsyncSession = Depends(get_project_db_async),
):
    return await crud_update_event_failure_mode(
        db=project_db,
        event_id=event_id,
        failure_mode_id=failure_mode.failure_mode_id,
    )


@router.put("/{event_id}/root-cause")
async def update_event_root_cause(
    root_cause: Annotated[interfaces.RootCauseUpdate, Body()],
    event_id: Annotated[int, Path(title="The ID of the event to update")],
    project_db: AsyncSession = Depends(get_project_db_async),
):
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


@router.get(
    "/windowed-events",
    response_model=list[interfaces.Event],
    response_model_exclude={"device_name_full"},
)
def get_windowed_events(
    start: datetime.datetime,
    end: datetime.datetime,
    project_db: Annotated[Session, Depends(get_project_db)],
    deep: bool = False,
):
    """Get events within a specific time window.

    This optimized version uses a single database query with
    appropriate joins when deep=True.
    """
    return core.crud.project.events.get_windowed_events(
        db=project_db, start=start, end=end, deep=deep
    ).models()


@router.get("/event-devices")
def get_event_devices(
    project_db: Annotated[Session, Depends(get_project_db)],
    db: Annotated[Session, Depends(get_db)],
):
    # First get all device IDs that have events in a single query
    device_ids = crud_get_event_device_ids(project_db)

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
    project: Annotated[models.Project, Depends(get_project)],
):
    """Generate a summary of events with their associated device, failure mode,
    root cause, and loss information.

    Args:
        project_db (Session): Project-specific database session
        db (Session): Main database session
        open (bool, optional): Filter for open events only. Defaults to True.
        start (datetime, optional): Start time for filtering events
        end (datetime, optional): End time for filtering events
        device_type_ids (list[int], optional): Filter events by device type IDs
        device_ids (list[int], optional): Filter events by device IDs
        project_id (UUID, optional): Project ID for timezone conversion

    Returns:
        list[EventSummary]: List of event summaries containing:
            - event_id: Unique identifier for the event
            - device_type_name: Name of the device type
            - device_name_full: Full name of the device
            - time_start: Event start time
            - time_end: Event end time
            - failure_mode: Name of the failure mode
            - root_cause: Name of the root cause
            - loss_total_financial: Total financial loss
            - loss_total_energy: Total energy loss
    """
    # Get timezone information
    if project_id:
        project_tz = project.time_zone
    else:
        project_tz = "UTC"
    tzinfo = ZoneInfo(project_tz)

    # Adjust timezone for start/end if provided
    if start is not None:
        start = start.astimezone(tzinfo)
    if end is not None:
        end = end.astimezone(tzinfo)

    # Get events with device information using the CRUD function
    events = crud_get_events_summary(
        project_db,
        open=open,
        start=start,
        end=end,
        device_type_ids=device_type_ids,
        device_ids=device_ids,
    )

    if not events:
        return []

    # Extract IDs for batch fetching
    event_ids = [event.event_id for event in events]
    failure_mode_ids = list(set(event.failure_mode_id for event in events))
    root_cause_ids = list(
        set(event.root_cause_id for event in events if event.root_cause_id is not None),
    )

    # Batch fetch all related data
    failure_modes = await get_failure_modes(db=db, failure_mode_ids=failure_mode_ids)
    failure_mode_id_to_name = {
        failure_mode.failure_mode_id: failure_mode.name_long
        for failure_mode in failure_modes
    }

    root_causes = await get_root_causes(db=db, root_cause_ids=root_cause_ids)
    root_cause_id_to_name = {
        root_cause.root_cause_id: root_cause.name_long for root_cause in root_causes
    }

    # Get event losses in a single query
    event_losses = core.crud.project.event_losses.get_event_losses(
        project_db, event_ids=event_ids
    ).models()

    # Process event losses once into a more efficient structure
    loss_data: dict[int, dict[str, Any]] = {}
    for loss in event_losses:
        event_id = loss.event_id
        if event_id not in loss_data:
            loss_data[event_id] = {"energy": 0.0, "financial": 0.0, "count": 0}

        loss_data[event_id]["count"] += 1
        if loss.event_loss_type_id == 1:  # Energy loss
            loss_data[event_id]["energy"] += loss.loss
        elif loss.event_loss_type_id == 2:  # Financial loss
            loss_data[event_id]["financial"] += loss.loss

    # Current time for calculating days elapsed for open events
    now = datetime.datetime.now(tzinfo)

    # Generate summaries
    summary = []
    for event in events:
        # Get device and type information directly from joined data
        device = event.device
        device_type = device.device_type if device else None

        device_type_name = device_type.name_long if device_type else "Unknown"
        device_name = device.name_long or ""
        device_name_full = f"{device_type_name} {device_name}"

        # Calculate days elapsed
        if event.time_end is not None:
            days_elapsed = (event.time_end - event.time_start).days
        else:
            days_elapsed = (now - event.time_start).days

        # Get loss data
        event_loss = loss_data.get(
            event.event_id,
            {"energy": 0.0, "financial": 0.0, "count": 0},
        )
        loss_count = event_loss["count"]
        energy = event_loss["energy"]
        financial = event_loss["financial"]

        # Calculate daily losses if we have loss data
        if loss_count > 0 and days_elapsed is not None and days_elapsed >= 0:
            loss_daily_energy = energy / (days_elapsed + 1)
            loss_daily_financial = financial / (days_elapsed + 1)

            summary.append(
                interfaces.EventSummary(
                    event_id=event.event_id,
                    device_type_name=device_type_name,
                    device_name_full=device_name_full,
                    time_start=event.time_start,
                    time_end=event.time_end,
                    failure_mode=failure_mode_id_to_name.get(
                        event.failure_mode_id,
                        "Unknown",
                    ),
                    root_cause=root_cause_id_to_name.get(
                        event.root_cause_id,
                        "Unknown",
                    ),
                    loss_total_financial=financial,
                    loss_total_energy=energy,
                    loss_daily_financial=loss_daily_financial,
                    loss_daily_energy=loss_daily_energy,
                ),
            )
        else:
            # Handle the case where we don't have loss data
            summary.append(
                interfaces.EventSummary(
                    event_id=event.event_id,
                    device_type_name=device_type_name,
                    device_name_full=device_name_full,
                    time_start=event.time_start,
                    time_end=event.time_end,
                    failure_mode=failure_mode_id_to_name.get(
                        event.failure_mode_id,
                        "Unknown",
                    ),
                    root_cause=root_cause_id_to_name.get(
                        event.root_cause_id,
                        "Unknown",
                    ),
                    loss_total_financial=None,
                    loss_total_energy=None,
                    loss_daily_financial=None,
                    loss_daily_energy=None,
                ),
            )

    return summary


@router.get("/uptime")
async def get_uptime(
    start: datetime.datetime,
    end: datetime.datetime,
    project_db: Annotated[Session, Depends(get_project_db)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    project: Annotated[models.Project, Depends(get_project)],
):
    # Query events from the database
    events = core.crud.project.events.get_windowed_events(
        db=project_db, start=start, end=end
    ).models()

    if not events:
        return []

    if project.project_type_id != 2:
        # Get POA data efficiently for daylight hours calculation
        poa_df = utils.data_df(
            project_db,
            project,
            tags=core.crud.project.tags.get_project_tags(
                db=project_db,
                sensor_type_name_shorts=["met_station_poa"],
                deep=False,
            ).models(),
            start=start,
            end=end,
            fillna_zero=False,
            get_last=False,
        )

        # Create a set of allowed downtime timestamps (more efficient than DatetimeIndex)
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
        # Convert timestamps to use the same UTC timezone object to avoid pandas timezone comparison issues
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

        # Skip tracker_pv_pcs (device_type_id = 10)
        if device.device_type_id == 10:
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
                "downtime_hours": data["hours"],
                "downtime_percentage": data["hours"] / possible_uptime,
                "events": data["count"],
            },
        )

    return result


@router.get("/event-trace-tags", response_model=list[interfaces.Tag])
def get_event_trace_tags(
    project_db: Annotated[Session, Depends(get_project_db)],
    device_id: int,
):
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
        case _:
            sentry_sdk.capture_exception(
                ValueError(f"Device type {device.device_type_id} not supported.")
            )
            raise HTTPException(
                status_code=400,
                detail="This device type is not yet supported. The Proximal Team has been notified.",
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
    project_db: Annotated[Session, Depends(get_project_db)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    try:
        if isinstance(start, str):
            start = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
        if isinstance(end, str):
            end = datetime.datetime.fromisoformat(end.replace("Z", "+00:00"))

        event_data = crud_get_events_with_device_info(
            project_db,
            time_end_gte=start,
            time_end_lt=end,
            open=False,
        )

        if not event_data:
            return {"data": pd.DataFrame().to_dict("tight")}

        event_ids = [event.event_id for event in event_data]
        event_losses = core.crud.project.event_losses.get_event_losses(
            project_db,
            event_ids=event_ids,
            time_gte=start,
            time_lt=end,
        ).models()

        failure_modes = await get_failure_modes(db=db)
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
                    "event_id": d.event_id,
                    "time_start": d.time_start,
                    "time_end": d.time_end,
                    "device_id": d.device_id,
                    "failure_mode": failure_mode_map.get(d.failure_mode_id, "Unknown"),
                    "root_cause": root_cause_map.get(d.root_cause_id or -1, "Unknown"),
                    "losses": event_losses_dict.get(d.event_id, []),
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


@router.get("/count-open")
def get_count_open(
    project_db: Annotated[Session, Depends(get_project_db)],
):
    x = crud_get_count_open(db=project_db)
    return x


@router.post("/bulk-create", response_model=interfaces.BulkCreateEventsResponse)
def bulk_create_events(
    project_db: Annotated[Session, Depends(get_project_db)],
    db: Annotated[Session, Depends(get_db)],
    project_id: uuid.UUID,
    payload: interfaces.BulkCreateEventsRequest,
):
    """Create events in bulk for a set of device_ids and attach a single loss row each.

    - Creates an `events` row per device with failure_mode_id default 1 (Generic Underperformance)
    - Inserts an `event_losses` row at `time_start` with provided loss and event_loss_type_id
    - If event_loss_type_id=3 is not present in operational.event_loss_types, create it with
      name_short 'proximal_pv_dc_capacity'.
    """
    # Ensure event_loss_type id exists (id 3 requested by frontend)
    loss_type_id = 3
    try:
        exists = (
            db.query(models.EventLossType)
            .filter(models.EventLossType.event_loss_type_id == loss_type_id)
            .first()
        )
        if not exists:
            new_type = models.EventLossType(
                event_loss_type_id=loss_type_id, name_short="proximal_pv_dc_capacity"
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
                f"SELECT setval( pg_get_serial_sequence('{project_name_short}.events', 'event_id'), "  # noqa: S608
                f"COALESCE((SELECT MAX(event_id) FROM {project_name_short}.events), 1), true )"  # noqa: S608
            )
        )
        project_db.execute(text("COMMIT"))

        # Map DC Combiner device_ids to their DC Field children (device_type_id = 30)
        combiner_device_ids = [item.device_id for item in payload.items]

        # Get DC Field devices that are direct children of our combiners
        dc_field_children = core.crud.project.devices.get_project_devices(
            project_db,
            device_type_ids=[30],  # DC Field device type
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
            # Use DC Field device_id if available, otherwise fall back to combiner device_id
            target_device_id = combiner_to_field_mapping.get(
                item.device_id, item.device_id
            )

            if target_device_id not in device_items:
                device_items[target_device_id] = []
            device_items[target_device_id].append(item)

        # Check for existing events to avoid conflicts
        target_device_ids = list(device_items.keys())
        existing_events = (
            project_db.query(models.Event)
            .filter(
                models.Event.device_id.in_(target_device_ids),
                models.Event.time_start >= payload.time_start,
                models.Event.time_start
                < payload.time_start + datetime.timedelta(seconds=len(payload.items)),
            )
            .all()
        )

        # Create a set of existing (device_id, time_start) combinations
        existing_combinations = {
            (event.device_id, event.time_start) for event in existing_events
        }

        # Create events and losses with proper event_id assignment
        created_event_ids = []
        losses_data = []
        event_to_anomalies_mapping = {}  # Track which event_id corresponds to which anomaly UUIDs
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
            from sqlalchemy import insert

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
    """
    Get all drone anomalies associated with a specific event.
    Anomalies are linked to events via the event_id column.
    """
    try:
        anomalies = crud_get_anomalies_by_event_id(db=project_db, event_id=event_id)
        return anomalies
    except Exception as e:
        logging.error(f"Failed to get anomalies for event {event_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve anomalies for event"
        )
