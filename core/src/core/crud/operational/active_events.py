"""Active Events CRUD operations for core package."""

import re
from typing import Any, Literal, cast
from uuid import UUID

import sqlalchemy as sa
from core.db_query import DbQuery
from sqlalchemy import bindparam, delete, func, insert, literal, select, text
from sqlalchemy.schema import Table
from sqlalchemy.sql.elements import BindParameter

from core import enumerations, models

_VALID_SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
# Namespace for ``pg_advisory_xact_lock`` so refresh locks do not collide
# with other advisory-lock users.
_ACTIVE_EVENTS_REFRESH_LOCK_NAMESPACE = 202605281
_ACTIVE_EVENT_COLUMNS = (
    "project_id",
    "event_id",
    "device_id",
    "device_type_id",
    "device_name_full",
    "failure_mode_id",
    "root_cause_id",
    "time_start",
    "loss_total_financial",
    "loss_total_energetic",
)


def _validated_tenant_schema(*, name_short: str) -> str:
    if not _VALID_SCHEMA_RE.fullmatch(name_short):
        raise ValueError(f"Invalid tenant schema name: {name_short!r}")
    return name_short


def _tenant_schema_table(*, base: Table, schema: str) -> Table:
    return sa.Table(
        base.name,
        sa.MetaData(),
        *[sa.Column(col.name, col.type) for col in base.columns],
        schema=schema,
    )


def _project_id_column(*, project_id: UUID | BindParameter[Any]) -> Any:
    if isinstance(project_id, UUID):
        return literal(project_id).label("project_id")
    return project_id.label("project_id")


def _build_open_events_select(
    *,
    project_id: UUID | BindParameter[Any],
    tenant_schema: str,
) -> sa.Select[Any]:
    events = _tenant_schema_table(
        base=cast(Table, models.Event.__table__),
        schema=tenant_schema,
    )
    devices = _tenant_schema_table(
        base=cast(Table, models.Device.__table__),
        schema=tenant_schema,
    )
    event_losses = _tenant_schema_table(
        base=cast(Table, models.EventLoss.__table__),
        schema=tenant_schema,
    )
    device_type = models.DeviceType.__table__
    loss_total_energetic = (
        select(func.sum(event_losses.c.loss))
        .where(
            event_losses.c.event_id == events.c.event_id,
            event_losses.c.event_loss_type_id
            == literal(enumerations.EventLossTypeEnum.PROXIMAL_ENERGY.value),
        )
        .correlate(events)
        .scalar_subquery()
    )
    device_name_full = func.trim(
        func.concat(
            func.coalesce(device_type.c.name_long, ""),
            " ",
            func.coalesce(devices.c.name_long, ""),
        )
    )
    return (
        select(
            _project_id_column(project_id=project_id),
            events.c.event_id,
            events.c.device_id,
            devices.c.device_type_id,
            device_name_full.label("device_name_full"),
            events.c.failure_mode_id,
            events.c.root_cause_id,
            events.c.time_start,
            events.c.loss_total_financial,
            loss_total_energetic.label("loss_total_energetic"),
        )
        .select_from(events)
        .join(devices, events.c.device_id == devices.c.device_id)
        .join(
            device_type,
            devices.c.device_type_id == device_type.c.device_type_id,
        )
        .where(events.c.time_end.is_(None))
    )


def lock_operational_active_events(
    *,
    project_id: UUID,
) -> DbQuery[Any, Literal[False]]:
    """Acquire a transaction-scoped advisory lock for a project refresh.

    ``ROW EXCLUSIVE`` table locks do not serialize concurrent refreshes
    because PostgreSQL allows multiple holders and refresh DML already
    acquires that mode. This lock blocks until no other transaction holds
    the same ``project_id`` refresh lock, then releases at commit/rollback.

    Run before ``delete_project_active_events`` and
    ``insert_project_active_events`` in the same transaction when
    concurrent refreshes for the same project must serialize.

    Args:
        project_id: Operational project UUID.

    Returns:
        ``DbQuery`` wrapping ``pg_advisory_xact_lock`` for ``project_id``.
    """
    lock_stmt = text(
        "SELECT pg_advisory_xact_lock("
        ":lock_namespace, hashtext(cast(:project_id AS text))"
        ")"
    ).bindparams(
        bindparam(
            "lock_namespace",
            value=_ACTIVE_EVENTS_REFRESH_LOCK_NAMESPACE,
            type_=sa.Integer(),
        ),
        bindparam(
            "project_id",
            value=project_id,
            type_=sa.Uuid(as_uuid=True),
        ),
    )
    return DbQuery(query=lock_stmt, is_scalar=False)


def delete_project_active_events(
    *,
    project_id: UUID,
) -> DbQuery[Any, Literal[False]]:
    """Delete denormalized active-event rows for a project.

    Run after ``lock_operational_active_events`` and before
    ``insert_project_active_events`` in the same transaction. Separate
    statements are required because PostgreSQL does not guarantee
    delete-before-insert when both touch ``operational.active_events``
    inside one data-modifying ``WITH`` clause.

    Args:
        project_id: Operational project UUID.

    Returns:
        ``DbQuery`` wrapping ``DELETE FROM operational.active_events``.
    """
    active_table = cast(Table, models.ActiveEvent.__table__)
    project_id_param = bindparam(
        "project_id",
        value=project_id,
        type_=sa.Uuid(as_uuid=True),
    )
    delete_stmt = delete(active_table).where(
        active_table.c.project_id == project_id_param,
    )
    return DbQuery(query=delete_stmt, is_scalar=False)


def insert_project_active_events(
    *,
    project_id: UUID,
    name_short: str,
) -> DbQuery[Any, Literal[False]]:
    """Insert open tenant events into operational.active_events.

    Open events are those with ``time_end IS NULL`` in the project schema.
    Run after ``lock_operational_active_events`` and
    ``delete_project_active_events`` in the same transaction.

    Args:
        project_id: Operational project UUID.
        name_short: Tenant schema name (validated before use in SQL).

    Returns:
        ``DbQuery`` wrapping ``INSERT … SELECT`` for open tenant events.
    """
    tenant_schema = _validated_tenant_schema(name_short=name_short)
    active_table = cast(Table, models.ActiveEvent.__table__)
    project_id_param = bindparam(
        "project_id",
        value=project_id,
        type_=sa.Uuid(as_uuid=True),
    )
    open_events = _build_open_events_select(
        project_id=project_id_param,
        tenant_schema=tenant_schema,
    )
    insert_stmt = insert(active_table).from_select(
        list(_ACTIVE_EVENT_COLUMNS),
        open_events,
    )
    return DbQuery(query=insert_stmt, is_scalar=False)
