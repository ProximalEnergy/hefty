import datetime
from typing import Any, Literal
from uuid import UUID

import sqlalchemy as sa
from core.db_query import DbQuery
from sqlalchemy.orm import noload, selectinload

from core import enumerations, models


def query_project_claims(
    *,
    project_id: UUID,
) -> DbQuery[Any, Literal[False]]:
    """Build a query for project claim summaries.

    Args:
        project_id: Operational project id to filter claim configs.
    """
    updates = (
        sa.select(
            models.ClaimUpdate.claim_id,
            sa.func.min(models.ClaimUpdate.created_at).label("created_at"),
            sa.func.max(models.ClaimUpdate.created_at).label("updated_at"),
        )
        .group_by(models.ClaimUpdate.claim_id)
        .subquery()
    )
    devices = (
        sa.select(
            models.ClaimDevice.claim_id,
            sa.func.count(models.ClaimDevice.claim_device_id).label("device_count"),
        )
        .group_by(models.ClaimDevice.claim_id)
        .subquery()
    )

    stmt = (
        sa.select(
            models.Claim.claim_id,
            models.Claim.claim_config_id,
            models.Claim.status,
            models.Claim.summary,
            models.Claim.external_reference,
            models.Company.name_long.label("counterparty_name"),
            updates.c.created_at,
            updates.c.updated_at,
            sa.func.coalesce(devices.c.device_count, 0).label("device_count"),
            models.ClaimDevice.event_id.label("claim_event_id"),
        )
        .join(
            models.ClaimConfig,
            models.Claim.claim_config_id == models.ClaimConfig.claim_config_id,
        )
        .join(
            models.Company,
            models.ClaimConfig.counterparty_company_id == models.Company.company_id,
        )
        .outerjoin(updates, updates.c.claim_id == models.Claim.claim_id)
        .outerjoin(devices, devices.c.claim_id == models.Claim.claim_id)
        .outerjoin(
            models.ClaimDevice,
            models.ClaimDevice.claim_id == models.Claim.claim_id,
        )
        .where(models.ClaimConfig.project_id == project_id)
        .order_by(
            models.Claim.claim_id.desc(),
            models.ClaimDevice.claim_device_id.asc(),
        )
    )
    return DbQuery(query=stmt)


def query_claim(
    *,
    claim_id: int,
    project_id: UUID | None = None,
) -> DbQuery[models.Claim, Literal[True]]:
    """Build a query for a single claim with related detail.

    Args:
        claim_id: Claim primary key.
        project_id: Optional operational project id scope.
    """
    stmt = (
        sa.select(models.Claim)
        .options(
            selectinload(models.Claim.devices).selectinload(models.ClaimDevice.device),
            selectinload(models.Claim.updates).options(
                selectinload(models.ClaimUpdate.user),
                noload(models.ClaimUpdate.attachments),
            ),
            selectinload(models.Claim.claim_config).selectinload(
                models.ClaimConfig.counterparty_company
            ),
            noload(models.Claim.attachments),
        )
        .where(models.Claim.claim_id == claim_id)
    )
    if project_id is not None:
        stmt = stmt.join(
            models.ClaimConfig,
            models.Claim.claim_config_id == models.ClaimConfig.claim_config_id,
        ).where(models.ClaimConfig.project_id == project_id)
    return DbQuery(query=stmt, is_scalar=True)


def get_claim_device(
    *,
    claim_id: int,
    claim_device_id: int,
) -> DbQuery[models.ClaimDevice, Literal[True]]:
    """Build a query for one claim device.

    Args:
        claim_id: Parent claim id.
        claim_device_id: Claim device primary key.
    """
    stmt = sa.select(models.ClaimDevice).where(
        models.ClaimDevice.claim_id == claim_id,
        models.ClaimDevice.claim_device_id == claim_device_id,
    )
    return DbQuery(query=stmt, is_scalar=True)


def get_claim_update(
    *,
    claim_update_id: int,
) -> DbQuery[models.ClaimUpdate, Literal[True]]:
    """Build a query for one claim update.

    Args:
        claim_update_id: Claim update primary key.
    """
    stmt = sa.select(models.ClaimUpdate).where(
        models.ClaimUpdate.claim_update_id == claim_update_id
    )
    return DbQuery(query=stmt, is_scalar=True)


def query_count_claims_for_config(
    *,
    claim_config_id: int,
) -> DbQuery[int, Literal[True]]:
    """Build a count query for claims linked to a claim config.

    Args:
        claim_config_id: Config id to inspect.
    """
    stmt = sa.select(sa.func.count()).where(
        models.Claim.claim_config_id == claim_config_id
    )
    return DbQuery(query=stmt, is_scalar=True)


def insert_claim(
    *,
    claim_config_id: int,
    status: enumerations.ClaimStatus,
    summary: str | None,
    external_reference: str | None,
) -> DbQuery[Any, Literal[True]]:
    """Build an insert for a claim row.

    Args:
        claim_config_id: FK to claim configs.
        status: Initial claim status.
        summary: Optional summary.
        external_reference: Optional external reference.
    """
    stmt = (
        sa.insert(models.Claim)
        .values(
            claim_config_id=claim_config_id,
            status=status,
            summary=summary,
            external_reference=external_reference,
        )
        .returning(models.Claim.claim_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


def query_update_claim(
    *,
    claim_id: int,
    values: dict[str, Any],
) -> DbQuery[Any, Literal[True]]:
    """Build an update for a claim row.

    Args:
        claim_id: Claim primary key.
        values: Column values to update.
    """
    stmt = (
        sa.update(models.Claim)
        .where(models.Claim.claim_id == claim_id)
        .values(**values)
        .returning(models.Claim.claim_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


def query_delete_claim(
    *,
    claim_id: int,
) -> DbQuery[Any, Literal[True]]:
    """Build a delete for a claim row.

    Args:
        claim_id: Claim primary key.
    """
    stmt = (
        sa.delete(models.Claim)
        .where(models.Claim.claim_id == claim_id)
        .returning(models.Claim.claim_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


def insert_claim_device(
    *,
    claim_id: int,
    device_id: int,
    event_id: int | None,
    oem_serial_number: str | None,
    oem_part_number: str | None,
    notes: str | None,
) -> DbQuery[Any, Literal[True]]:
    """Build an insert for a claim device row.

    Args:
        claim_id: Parent claim id.
        device_id: Device id.
        event_id: Optional event id.
        oem_serial_number: OEM serial number.
        oem_part_number: OEM part number.
        notes: Free-text notes.
    """
    stmt = (
        sa.insert(models.ClaimDevice)
        .values(
            claim_id=claim_id,
            device_id=device_id,
            event_id=event_id,
            oem_serial_number=oem_serial_number,
            oem_part_number=oem_part_number,
            notes=notes,
        )
        .returning(models.ClaimDevice.claim_device_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


def query_update_claim_device(
    *,
    claim_id: int,
    claim_device_id: int,
    values: dict[str, Any],
) -> DbQuery[Any, Literal[True]]:
    """Build an update for a claim device row.

    Args:
        claim_id: Parent claim id.
        claim_device_id: Claim device primary key.
        values: Column values to update.
    """
    stmt = (
        sa.update(models.ClaimDevice)
        .where(
            models.ClaimDevice.claim_id == claim_id,
            models.ClaimDevice.claim_device_id == claim_device_id,
        )
        .values(**values)
        .returning(models.ClaimDevice.claim_device_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


def query_delete_claim_device(
    *,
    claim_id: int,
    claim_device_id: int,
) -> DbQuery[Any, Literal[True]]:
    """Build a delete for a claim device row.

    Args:
        claim_id: Parent claim id.
        claim_device_id: Claim device primary key.
    """
    stmt = (
        sa.delete(models.ClaimDevice)
        .where(
            models.ClaimDevice.claim_id == claim_id,
            models.ClaimDevice.claim_device_id == claim_device_id,
        )
        .returning(models.ClaimDevice.claim_device_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


def delete_claim_devices(
    *,
    claim_id: int,
) -> DbQuery[Any, Literal[False]]:
    """Build a delete for all devices attached to a claim.

    Args:
        claim_id: Parent claim id.
    """
    stmt = sa.delete(models.ClaimDevice).where(models.ClaimDevice.claim_id == claim_id)
    return DbQuery(query=stmt)


def insert_claim_update(
    *,
    claim_id: int,
    user_id: str,
    update_type: enumerations.ClaimUpdateType,
    from_status: enumerations.ClaimStatus | None,
    to_status: enumerations.ClaimStatus | None,
    message: str | None,
    created_at: datetime.datetime | None = None,
) -> DbQuery[Any, Literal[True]]:
    """Build an insert for a claim update row.

    Args:
        claim_id: Parent claim id.
        user_id: User performing the action.
        update_type: Update type.
        from_status: Previous status, if any.
        to_status: New status, if any.
        message: Optional message.
        created_at: Optional backdated timestamp.
    """
    values: dict[str, Any] = {
        "claim_id": claim_id,
        "update_type": update_type,
        "from_status": from_status,
        "to_status": to_status,
        "message": message,
        "user_id": user_id,
    }
    if created_at is not None:
        values["created_at"] = created_at
    stmt = (
        sa.insert(models.ClaimUpdate)
        .values(**values)
        .returning(models.ClaimUpdate.claim_update_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


def delete_claim_updates(
    *,
    claim_id: int,
) -> DbQuery[Any, Literal[False]]:
    """Build a delete for all updates attached to a claim.

    Args:
        claim_id: Parent claim id.
    """
    stmt = sa.delete(models.ClaimUpdate).where(models.ClaimUpdate.claim_id == claim_id)
    return DbQuery(query=stmt)
