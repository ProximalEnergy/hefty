import datetime
from typing import Literal, cast

import core.crud.project.devices as crud_devices
import core.models as models
import pandas as pd
import sqlalchemy as sa
from core.db_query import DbQuery, OutputType
from core.enumerations import DeviceTypeEnum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import ClauseElement


def get_event_cmms_tickets(
    *,
    event_cmms_ticket_ids: list[int] | None = None,
    event_ids: list[int] | None = None,
    cmms_ticket_ids: list[int] | None = None,
    created_by_user_ids: list[str] | None = None,
    created_at_gte: datetime.datetime | None = None,
    created_at_lte: datetime.datetime | None = None,
) -> DbQuery[models.EventCMMSTicket, Literal[False]]:
    """
    Retrieve event-CMMS ticket relationships by various filters.

    Args:
        event_cmms_ticket_ids: Filter by event-CMMS ticket ids.
        event_ids: Filter by event ids.
        cmms_ticket_ids: Filter by CMMS ticket ids.
        created_by_user_ids: Filter by created by user ids.
        created_at_gte: Filter by created at greater than or equal to.
        created_at_lte: Filter by created at less than or equal to.
    """
    model = models.EventCMMSTicket
    stmt = sa.select(model)

    if event_cmms_ticket_ids is not None:
        stmt = stmt.where(model.event_cmms_ticket_id.in_(event_cmms_ticket_ids))
    if event_ids is not None:
        stmt = stmt.where(model.event_id.in_(event_ids))
    if cmms_ticket_ids is not None:
        stmt = stmt.where(model.cmms_ticket_id.in_(cmms_ticket_ids))
    if created_by_user_ids is not None:
        stmt = stmt.where(model.created_by_user_id.in_(created_by_user_ids))
    if created_at_gte is not None:
        stmt = stmt.where(model.created_at >= created_at_gte)
    if created_at_lte is not None:
        stmt = stmt.where(model.created_at <= created_at_lte)

    return DbQuery(query=stmt)


async def add_event_cmms_ticket(
    *,
    db: AsyncSession,
    event_id: int,
    cmms_ticket_id: int,
    created_by_user_id: str,
) -> models.EventCMMSTicket:
    """
    Add a new event-CMMS ticket relationship.

    Args:
        db: The database session.
        event_id: The event ID.
        cmms_ticket_id: The CMMS ticket ID.
        created_by_user_id: The user ID of the creator.
    """
    event_cmms_ticket = models.EventCMMSTicket(
        event_id=event_id,
        cmms_ticket_id=cmms_ticket_id,
        created_by_user_id=created_by_user_id,
    )
    db.add(event_cmms_ticket)
    await db.commit()
    await db.refresh(event_cmms_ticket)
    return event_cmms_ticket


async def delete_event_cmms_ticket(
    *,
    db: AsyncSession,
    event_cmms_ticket_id: int,
) -> models.EventCMMSTicket | None:
    """
    Delete an event-CMMS ticket relationship.

    Args:
        db: The database session.
        event_cmms_ticket_id: The event-CMMS ticket ID.
    """
    model = models.EventCMMSTicket
    stmt = sa.select(model).where(model.event_cmms_ticket_id == event_cmms_ticket_id)
    result = await db.execute(stmt)
    event_cmms_ticket = result.scalar_one_or_none()

    if event_cmms_ticket:
        await db.delete(event_cmms_ticket)
        await db.commit()
        return event_cmms_ticket
    return None


async def get_suggested_events_with_score_from_ticket(
    *,
    cmms_ticket_id: int,
    cmms_integration_id: int,
    cmms_device_id: str | None = None,
    source_created_at: datetime.datetime | None = None,
    project: models.Project,
    project_db: AsyncSession,
    limit: int = 10,
):
    """
    Get suggested events from a ticket, with a computed score.

    Args:
        cmms_ticket_id: ID of the CMMS ticket to find event suggestions
            for.
        cmms_integration_id: ID of the CMMS integration the ticket
            belongs to.
        cmms_device_id: External device ID from the CMMS system. Used
            to narrow candidate events by device. Optional.
        source_created_at: Timestamp from the originating CMMS system
            when the ticket was created. Used for time-proximity
            scoring. Optional.
        project: The project context used to scope the event search.
        project_db: Async database session for the project database.
        limit: Maximum number of suggested events to return.
            Defaults to 10.

    Returns:
        list[tuple[models.Event, int]] where each tuple is
        (event, score).
    """
    ct = models.CMMSTicket
    cd = models.CMMSDevice
    e = models.Event
    d = models.Device

    has_device = cmms_device_id is not None
    has_time = source_created_at is not None
    if not has_device and not has_time:
        return []

    ticket_internal_device_id: int | None = None
    device_ids: set[int] = set()
    parent_child_ids: set[int] = set()
    other_ids: set[int] = set()

    desc_cols = ["device_id", "device_id_path"]
    descendent_devices_df = pd.DataFrame(columns=desc_cols)
    ancestor_devices_df = pd.DataFrame(columns=desc_cols)
    ticket_device_path: str | None = None

    if has_device:
        # 1) Resolve internal device_id for this ticket
        stmt = (
            sa.select(cd.device_id)
            .select_from(ct)
            .join(
                cd,
                sa.and_(
                    ct.cmms_device_id == cd.cmms_device_id,
                    ct.cmms_integration_id == cd.cmms_integration_id,
                ),
            )
            .where(ct.cmms_ticket_id == cmms_ticket_id)
            .where(ct.cmms_integration_id == cmms_integration_id)
            .where(ct.cmms_device_id == str(cmms_device_id))
        )
        res = await project_db.execute(stmt)
        raw_device_id = res.scalars().first()
        if raw_device_id is not None:
            ticket_internal_device_id = int(raw_device_id)
            device_ids.add(ticket_internal_device_id)

            desc_query = crud_devices.get_project_devices(
                device_id_descendent_of=ticket_internal_device_id
            )
            desc_df = await desc_query.get_async(
                output_type=OutputType.PANDAS, schema=project.name_short
            )
            if desc_df is not None:
                descendent_devices_df = desc_df

            if not descendent_devices_df.empty:
                path_vals = descendent_devices_df.loc[
                    descendent_devices_df["device_id"] == ticket_internal_device_id,
                    "device_id_path",
                ].values
                if len(path_vals) > 0:
                    ticket_device_path = str(path_vals[0])

            if ticket_device_path is not None:
                ancestor_query = crud_devices.get_project_devices(
                    device_id_path_ancestor_of=ticket_device_path
                )
                ancestor_df = await ancestor_query.get_async(
                    output_type=OutputType.PANDAS, schema=project.name_short
                )
                if ancestor_df is not None:
                    ancestor_devices_df = ancestor_df

            if not descendent_devices_df.empty:
                device_ids.update(
                    descendent_devices_df["device_id"].astype(int).tolist()
                )
            if not ancestor_devices_df.empty:
                device_ids.update(ancestor_devices_df["device_id"].astype(int).tolist())
        elif not has_time:
            return []

    if ticket_device_path is not None:
        parent_device_id: int | None = None
        parts = ticket_device_path.split(".")
        if len(parts) >= 2:
            try:
                parent_device_id = int(parts[-2])
            except ValueError:
                parent_device_id = None

        ticket_depth = len(parts)
        prefix = f"{ticket_device_path}."
        child_device_ids: set[int] = set()
        if (
            not descendent_devices_df.empty
            and "device_id_path" in descendent_devices_df
        ):
            path_series = descendent_devices_df["device_id_path"].astype(str)
            child_mask = path_series.str.startswith(prefix)
            child_df = descendent_devices_df.loc[child_mask].copy()
            if not child_df.empty:
                depth_series = (
                    child_df["device_id_path"].astype(str).str.count(r"\.") + 1
                )
                child_df = child_df.loc[depth_series == (ticket_depth + 1)]
                if not child_df.empty:
                    child_device_ids = set(child_df["device_id"].astype(int).tolist())

        parent_child_ids = set(child_device_ids)
        if parent_device_id is not None:
            parent_child_ids.add(parent_device_id)
            device_ids.add(parent_device_id)

    if device_ids:
        other_ids = set(device_ids)
        if ticket_internal_device_id is not None:
            other_ids.discard(ticket_internal_device_id)
        other_ids -= parent_child_ids

    total_score_expr: ClauseElement = sa.literal(0)
    where_conditions: list = []
    event_end_eff = sa.func.coalesce(e.time_end, sa.func.now())

    if has_time:
        source_dt = cast(datetime.datetime, source_created_at)
        source_ts = pd.Timestamp(source_dt)
        if source_ts.tzinfo is None:
            created_at_local = source_ts.tz_localize(project.time_zone)
        else:
            created_at_local = source_ts.tz_convert(project.time_zone)

        buffer = pd.Timedelta(days=3)
        ticket_window_end = created_at_local + buffer
        ticket_window_start = created_at_local - buffer

        ticket_ts = sa.literal(created_at_local.to_pydatetime())
        within_event_window = sa.and_(
            ticket_ts >= e.time_start,
            ticket_ts <= event_end_eff,
        )

        seconds_24h = 24 * 60 * 60
        near_start = (
            sa.func.abs(sa.extract("epoch", e.time_start - ticket_ts)) <= seconds_24h
        )
        near_end = (
            sa.func.abs(sa.extract("epoch", event_end_eff - ticket_ts)) <= seconds_24h
        )

        time_score = sa.case(
            (within_event_window, sa.literal(50)),
            (sa.or_(near_start, near_end), sa.literal(20)),
            else_=sa.literal(0),
        )
        total_score_expr = total_score_expr + time_score

        where_conditions.extend(
            [
                e.time_start < ticket_window_end.to_pydatetime(),
                event_end_eff > ticket_window_start.to_pydatetime(),
            ]
        )

    if ticket_internal_device_id is not None:
        parent_child_list = sorted(parent_child_ids)
        other_list = sorted(other_ids)
        device_score = sa.case(
            (
                e.device_id == sa.literal(ticket_internal_device_id),
                sa.literal(100),
            ),
            (
                e.device_id.in_(parent_child_list)
                if parent_child_list
                else sa.literal(False),
                sa.literal(50),
            ),
            (
                e.device_id.in_(other_list) if other_list else sa.literal(False),
                sa.literal(10),
            ),
            else_=sa.literal(0),
        )
        total_score_expr = total_score_expr + device_score

    if device_ids:
        device_list = sorted(device_ids)
        where_conditions.append(e.device_id.in_(device_list))

    tracker_penalty_types = [
        DeviceTypeEnum.TRACKER_ROW.value,
        DeviceTypeEnum.TRACKER_ZONE.value,
    ]
    tracker_penalty = sa.case(
        (d.device_type_id.in_(tracker_penalty_types), sa.literal(-20)),
        else_=sa.literal(0),
    )
    total_score_expr = total_score_expr + tracker_penalty

    total_score = total_score_expr.label("score")

    stmt = sa.select(e, total_score).join(d, d.device_id == e.device_id)
    if where_conditions:
        stmt = stmt.where(*where_conditions)
    stmt = stmt.order_by(total_score.desc(), e.time_start.desc()).limit(limit)

    res = await project_db.execute(stmt)
    rows = res.all()  # list[Row] where each row = (Event, score)

    # Convert score to int defensively
    return [(row[0], int(row[1] or 0)) for row in rows]


async def get_suggested_tickets_with_score_from_event(
    *,
    event: models.Event,
    cmms_integration_id: int,
    project: models.Project,
    project_db: AsyncSession,
    limit: int = 10,
) -> list[tuple[models.CMMSTicket, int]]:
    """
    Get suggested CMMS tickets from an event, with a computed score.

    Args:
        event: The source event to match tickets against.
        cmms_integration_id: The CMMS integration identifier.
        project: The project associated with the event.
        project_db: Async database session scoped to the project schema.
        limit: Maximum number of results to return.

    Returns:
        list[tuple[models.CMMSTicket, int]] where each tuple is (ticket, score)
    """
    ct = models.CMMSTicket
    cd = models.CMMSDevice
    d = models.Device

    event_device_id = event.device_id
    if event_device_id is None:
        return []

    device_ids: set[int] = {event_device_id}
    parent_child_ids: set[int] = set()
    other_ids: set[int] = set()

    desc_cols = ["device_id", "device_id_path"]
    descendent_devices_df = pd.DataFrame(columns=desc_cols)
    ancestor_devices_df = pd.DataFrame(columns=desc_cols)
    event_device_path: str | None = None

    desc_query = crud_devices.get_project_devices(
        device_id_descendent_of=event_device_id
    )
    desc_df = await desc_query.get_async(
        output_type=OutputType.PANDAS, schema=project.name_short
    )
    if desc_df is not None:
        descendent_devices_df = desc_df

    if not descendent_devices_df.empty:
        path_vals = descendent_devices_df.loc[
            descendent_devices_df["device_id"] == event_device_id,
            "device_id_path",
        ].values
        if len(path_vals) > 0:
            event_device_path = str(path_vals[0])

    if event_device_path is not None:
        ancestor_query = crud_devices.get_project_devices(
            device_id_path_ancestor_of=event_device_path
        )
        ancestor_df = await ancestor_query.get_async(
            output_type=OutputType.PANDAS, schema=project.name_short
        )
        if ancestor_df is not None:
            ancestor_devices_df = ancestor_df

    if not descendent_devices_df.empty:
        device_ids.update(descendent_devices_df["device_id"].astype(int).tolist())
    if not ancestor_devices_df.empty:
        device_ids.update(ancestor_devices_df["device_id"].astype(int).tolist())

    if event_device_path is not None:
        parent_device_id: int | None = None
        parts = event_device_path.split(".")
        if len(parts) >= 2:
            try:
                parent_device_id = int(parts[-2])
            except ValueError:
                parent_device_id = None

        ticket_depth = len(parts)
        prefix = f"{event_device_path}."
        child_device_ids: set[int] = set()
        if (
            not descendent_devices_df.empty
            and "device_id_path" in descendent_devices_df
        ):
            path_series = descendent_devices_df["device_id_path"].astype(str)
            child_mask = path_series.str.startswith(prefix)
            child_df = descendent_devices_df.loc[child_mask].copy()
            if not child_df.empty:
                depth_series = (
                    child_df["device_id_path"].astype(str).str.count(r"\.") + 1
                )
                child_df = child_df.loc[depth_series == (ticket_depth + 1)]
                if not child_df.empty:
                    child_device_ids = set(child_df["device_id"].astype(int).tolist())

        parent_child_ids = set(child_device_ids)
        if parent_device_id is not None:
            parent_child_ids.add(parent_device_id)
            device_ids.add(parent_device_id)

    if device_ids:
        other_ids = set(device_ids)
        other_ids.discard(event_device_id)
        other_ids -= parent_child_ids

    total_score_expr: ClauseElement = sa.literal(0)
    where_conditions: list = [ct.cmms_integration_id == cmms_integration_id]

    event_start_dt = cast(datetime.datetime, event.time_start)
    event_start_ts = pd.Timestamp(event_start_dt)
    if event_start_ts.tzinfo is None:
        event_start_local = event_start_ts.tz_localize(project.time_zone)
    else:
        event_start_local = event_start_ts.tz_convert(project.time_zone)

    if event.time_end is not None:
        event_end_dt = cast(datetime.datetime, event.time_end)
        event_end_ts = pd.Timestamp(event_end_dt)
        if event_end_ts.tzinfo is None:
            event_end_local = event_end_ts.tz_localize(project.time_zone)
        else:
            event_end_local = event_end_ts.tz_convert(project.time_zone)
    else:
        event_end_local = pd.Timestamp.now(tz=project.time_zone)

    buffer = pd.Timedelta(days=3)
    event_window_start = event_start_local - buffer
    event_window_end = event_end_local + buffer

    event_start_literal = sa.literal(event_start_local.to_pydatetime())
    event_end_literal = sa.literal(event_end_local.to_pydatetime())
    window_start_dt = event_window_start.to_pydatetime()
    window_end_dt = event_window_end.to_pydatetime()

    ticket_ts = ct.source_created_at
    within_event_window = sa.and_(
        ticket_ts >= event_start_literal,
        ticket_ts <= event_end_literal,
    )

    seconds_24h = 24 * 60 * 60
    near_start = (
        sa.func.abs(sa.extract("epoch", ticket_ts - event_start_literal)) <= seconds_24h
    )
    near_end = (
        sa.func.abs(sa.extract("epoch", event_end_literal - ticket_ts)) <= seconds_24h
    )

    time_score = sa.case(
        (within_event_window, sa.literal(50)),
        (sa.or_(near_start, near_end), sa.literal(20)),
        else_=sa.literal(0),
    )
    total_score_expr = total_score_expr + time_score

    where_conditions.extend(
        [
            ct.source_created_at <= window_end_dt,
            ct.source_created_at >= window_start_dt,
        ]
    )

    parent_child_list = sorted(parent_child_ids)
    other_list = sorted(other_ids)
    device_score = sa.case(
        (cd.device_id == sa.literal(event_device_id), sa.literal(100)),
        (
            cd.device_id.in_(parent_child_list)
            if parent_child_list
            else sa.literal(False),
            sa.literal(50),
        ),
        (
            cd.device_id.in_(other_list) if other_list else sa.literal(False),
            sa.literal(10),
        ),
        else_=sa.literal(0),
    )
    total_score_expr = total_score_expr + device_score

    if device_ids:
        device_list = sorted(device_ids)
        where_conditions.append(cd.device_id.in_(device_list))

    tracker_penalty_types = [
        DeviceTypeEnum.TRACKER_ROW.value,
        DeviceTypeEnum.TRACKER_ZONE.value,
    ]
    tracker_penalty = sa.case(
        (d.device_type_id.in_(tracker_penalty_types), sa.literal(-20)),
        else_=sa.literal(0),
    )
    total_score_expr = total_score_expr + tracker_penalty

    total_score = total_score_expr.label("score")

    stmt = (
        sa.select(ct, total_score)
        .join(
            cd,
            sa.and_(
                cd.cmms_device_id == ct.cmms_device_id,
                cd.cmms_integration_id == ct.cmms_integration_id,
            ),
        )
        .join(d, d.device_id == cd.device_id)
    )
    if where_conditions:
        stmt = stmt.where(*where_conditions)
    stmt = stmt.order_by(total_score.desc(), ct.source_created_at.desc()).limit(limit)

    res = await project_db.execute(stmt)
    rows = res.all()  # list[Row] where each row = (CMMSTicket, score)

    # Convert score to int defensively
    return [(row[0], int(row[1] or 0)) for row in rows]
