"""CRUD operations for warranty claims."""

import datetime
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

import pandas as pd
from core.crud.operational import claim_configs as claim_config_queries
from core.crud.project import claim_attachments as claim_attachment_queries
from core.crud.project import claims as claim_queries
from core.db_query import OutputType
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models


def _none_if_missing(*, value: Any) -> Any:
    """Convert pandas missing sentinels to plain None.

    Args:
        value: Value from a dataframe record.
    """
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return list(value)
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        return value
    return value


def _records_from_dataframe(*, df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a dataframe to API-safe record dictionaries.

    Args:
        df: Query result dataframe.
    """
    return [
        {str(key): _none_if_missing(value=value) for key, value in record.items()}
        for record in df.to_dict("records")
    ]


def _project_claim_records_from_dataframe(
    *,
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Fold joined claim/device rows into one summary per claim.

    Args:
        df: Query result dataframe.
    """
    records_by_claim_id: dict[int, dict[str, Any]] = {}
    for record in _records_from_dataframe(df=df):
        claim_id = int(record["claim_id"])
        claim_record = records_by_claim_id.get(claim_id)
        if claim_record is None:
            claim_record = {
                key: value for key, value in record.items() if key != "claim_event_id"
            }
            claim_record["device_count"] = int(claim_record.get("device_count") or 0)
            claim_record["claim_event_ids"] = []
            records_by_claim_id[claim_id] = claim_record

        claim_event_id = record.get("claim_event_id")
        if claim_event_id is not None:
            claim_record["claim_event_ids"].append(int(claim_event_id))
    return list(records_by_claim_id.values())


def _returned_int(*, row: Any, key: str) -> int | None:
    """Read an integer id from a DML RETURNING row.

    Args:
        row: Row returned from a write query.
        key: Column key to read.
    """
    if row is None or not isinstance(row, Mapping):
        return None
    value = row.get(key)
    return int(value) if value is not None else None


async def get_project_claims(
    db: AsyncSession,
    *,
    project_id: UUID,
) -> list[dict[str, Any]]:
    """List claims for a project with config + company info.

    Args:
        db: Async DB session.
        project_id: Project to filter by.
    """
    df = await claim_queries.query_project_claims(
        project_id=project_id,
    ).get_async(
        executor=db,
        output_type=OutputType.PANDAS,
    )
    return _project_claim_records_from_dataframe(df=cast(pd.DataFrame, df))


async def create_claim(
    db: AsyncSession,
    *,
    claim_config_id: int,
    user_id: str,
    summary: str | None = None,
    external_reference: str | None = None,
) -> models.Claim:
    """Create a draft claim with an initial update.

    Args:
        db: Async DB session.
        claim_config_id: FK to claim_configs.
        user_id: Authenticated user id.
        summary: Optional summary text.
        external_reference: Optional ref.
    """
    row = await claim_queries.insert_claim(
        claim_config_id=claim_config_id,
        status=enumerations.ClaimStatus.DRAFT,
        summary=summary,
        external_reference=external_reference,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    claim_id = _returned_int(row=row, key="claim_id")
    if claim_id is None:
        raise RuntimeError("Failed to create claim")

    await claim_queries.insert_claim_update(
        claim_id=claim_id,
        user_id=user_id,
        update_type=enumerations.ClaimUpdateType.STATUS_CHANGE,
        from_status=None,
        to_status=enumerations.ClaimStatus.DRAFT,
        message="Claim created as draft",
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    await db.commit()
    claim = await claim_queries.query_claim(claim_id=claim_id).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    claim = cast(models.Claim | None, claim)
    if claim is None:
        raise RuntimeError("Failed to load created claim")
    return claim


async def update_claim(
    db: AsyncSession,
    *,
    claim_id: int,
    summary: str | None = None,
    external_reference: str | None = None,
    status: enumerations.ClaimStatus | None = None,
) -> models.Claim | None:
    """Update mutable fields on a claim.

    Args:
        db: Async DB session.
        claim_id: Claim primary key.
        summary: New summary if provided.
        external_reference: New reference if provided.
        status: New status if provided.
    """
    values: dict[str, Any] = {}
    if summary is not None:
        values["summary"] = summary
    if external_reference is not None:
        values["external_reference"] = external_reference
    if status is not None:
        values["status"] = status

    if not values:
        claim = await claim_queries.query_claim(claim_id=claim_id).get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        )
        return cast(models.Claim | None, claim)

    row = await claim_queries.query_update_claim(
        claim_id=claim_id,
        values=values,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    updated_claim_id = _returned_int(row=row, key="claim_id")
    if updated_claim_id is None:
        return None
    await db.commit()
    claim = await claim_queries.query_claim(claim_id=updated_claim_id).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    return cast(models.Claim | None, claim)


async def create_claim_device(
    db: AsyncSession,
    *,
    claim_id: int,
    device_id: int,
    event_id: int | None = None,
    oem_serial_number: str | None = None,
    oem_part_number: str | None = None,
    notes: str | None = None,
) -> models.ClaimDevice:
    """Add a device to a claim.

    Args:
        db: Async DB session.
        claim_id: Parent claim id.
        device_id: Device id.
        event_id: Optional event id.
        oem_serial_number: OEM serial.
        oem_part_number: OEM part number.
        notes: Free-text notes.
    """
    row = await claim_queries.insert_claim_device(
        claim_id=claim_id,
        device_id=device_id,
        event_id=event_id,
        oem_serial_number=oem_serial_number,
        oem_part_number=oem_part_number,
        notes=notes,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    claim_device_id = _returned_int(row=row, key="claim_device_id")
    if claim_device_id is None:
        raise RuntimeError("Failed to create claim device")
    await db.commit()
    claim_device = await claim_queries.get_claim_device(
        claim_id=claim_id,
        claim_device_id=claim_device_id,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    if claim_device is None:
        raise RuntimeError("Failed to load created claim device")
    return cast(models.ClaimDevice, claim_device)


async def delete_claim(
    db: AsyncSession,
    *,
    claim_id: int,
) -> bool:
    """Delete a draft claim and its devices/updates.

    Args:
        db: Async DB session.
        claim_id: Claim primary key.
    """
    await claim_attachment_queries.delete_claim_attachments_metadata(
        claim_id=claim_id,
    ).execute_async(
        executor=db,
    )
    await claim_queries.delete_claim_updates(
        claim_id=claim_id,
    ).execute_async(
        executor=db,
    )
    await claim_queries.delete_claim_devices(
        claim_id=claim_id,
    ).execute_async(
        executor=db,
    )
    row = await claim_queries.query_delete_claim(
        claim_id=claim_id,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    await db.commit()
    return _returned_int(row=row, key="claim_id") is not None


async def update_claim_device(
    db: AsyncSession,
    *,
    claim_id: int,
    claim_device_id: int,
    device_id: int | None = None,
    event_id: int | None = None,
    oem_serial_number: str | None = None,
    oem_part_number: str | None = None,
    notes: str | None = None,
) -> models.ClaimDevice | None:
    """Update fields on a claim device.

    Args:
        db: Async DB session.
        claim_id: Parent claim id.
        claim_device_id: PK of claim_device.
        device_id: New device_id (optional).
        event_id: New event_id (optional).
        oem_serial_number: New serial (optional).
        oem_part_number: New part number (optional).
        notes: New notes (optional).
    """
    values: dict[str, Any] = {}
    if device_id is not None:
        values["device_id"] = device_id
    if event_id is not None:
        values["event_id"] = event_id
    if oem_serial_number is not None:
        values["oem_serial_number"] = oem_serial_number or None
    if oem_part_number is not None:
        values["oem_part_number"] = oem_part_number or None
    if notes is not None:
        values["notes"] = notes or None

    if not values:
        claim_device = await claim_queries.get_claim_device(
            claim_id=claim_id,
            claim_device_id=claim_device_id,
        ).get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        )
        return cast(models.ClaimDevice | None, claim_device)

    row = await claim_queries.query_update_claim_device(
        claim_id=claim_id,
        claim_device_id=claim_device_id,
        values=values,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    updated_claim_device_id = _returned_int(row=row, key="claim_device_id")
    if updated_claim_device_id is None:
        return None
    await db.commit()
    claim_device = await claim_queries.get_claim_device(
        claim_id=claim_id,
        claim_device_id=updated_claim_device_id,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    return cast(models.ClaimDevice | None, claim_device)


async def delete_claim_device(
    db: AsyncSession,
    *,
    claim_id: int,
    claim_device_id: int,
) -> bool:
    """Remove a device from a claim.

    Args:
        db: Async DB session.
        claim_id: Parent claim id.
        claim_device_id: PK of claim_device.
    """
    row = await claim_queries.query_delete_claim_device(
        claim_id=claim_id,
        claim_device_id=claim_device_id,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    await db.commit()
    return _returned_int(row=row, key="claim_device_id") is not None


async def create_claim_update(
    db: AsyncSession,
    *,
    claim_id: int,
    user_id: str,
    update_type: enumerations.ClaimUpdateType,
    from_status: enumerations.ClaimStatus | None = None,
    to_status: enumerations.ClaimStatus | None = None,
    message: str | None = None,
    created_at: datetime.datetime | None = None,
) -> models.ClaimUpdate:
    """Record a claim update (note, status change, etc).

    Args:
        db: Async DB session.
        claim_id: Parent claim id.
        user_id: User performing the action.
        update_type: Type of update.
        from_status: Previous status if applicable.
        to_status: New status if applicable.
        message: Optional message.
        created_at: Optional backdated timestamp (for historical claims).
    """
    row = await claim_queries.insert_claim_update(
        claim_id=claim_id,
        user_id=user_id,
        update_type=update_type,
        from_status=from_status,
        to_status=to_status,
        message=message,
        created_at=created_at,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    claim_update_id = _returned_int(row=row, key="claim_update_id")
    if claim_update_id is None:
        raise RuntimeError("Failed to create claim update")
    await db.commit()
    claim_update = await claim_queries.get_claim_update(
        claim_update_id=claim_update_id,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    if claim_update is None:
        raise RuntimeError("Failed to load created claim update")
    return cast(models.ClaimUpdate, claim_update)


async def get_claim_configs(
    db: AsyncSession,
    *,
    project_id: UUID,
    submitter_company_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """List claim configs for a project with company names.

    Args:
        db: Async DB session.
        project_id: Filter by project.
        submitter_company_id: Filter by submitter.
    """
    df = await claim_config_queries.query_claim_configs(
        project_id=project_id,
        submitter_company_id=submitter_company_id,
    ).get_async(
        executor=db,
        output_type=OutputType.PANDAS,
    )
    return _records_from_dataframe(df=cast(pd.DataFrame, df))


async def create_claim_config(
    db: AsyncSession,
    *,
    submitter_company_id: UUID,
    counterparty_company_id: UUID,
    project_id: UUID | None = None,
    default_submission_channel: enumerations.ClaimSubmissionChannel,
    default_contact: str | None = None,
    portal_url: str | None = None,
) -> models.ClaimConfig:
    """Create a new claim config.

    Args:
        db: Async DB session.
        submitter_company_id: Company filing claims.
        counterparty_company_id: OEM / counterparty.
        project_id: Optional project scope.
        default_submission_channel: How claims are sent.
        default_contact: Contact email/name.
        portal_url: OEM portal URL.
    """
    row = await claim_config_queries.insert_claim_config(
        submitter_company_id=submitter_company_id,
        counterparty_company_id=counterparty_company_id,
        project_id=project_id,
        default_submission_channel=default_submission_channel,
        default_contact=default_contact,
        portal_url=portal_url,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    claim_config_id = _returned_int(row=row, key="claim_config_id")
    if claim_config_id is None:
        raise RuntimeError("Failed to create claim config")
    await db.commit()
    claim_config = await claim_config_queries.query_claim_config(
        claim_config_id=claim_config_id,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    claim_config = cast(models.ClaimConfig | None, claim_config)
    if claim_config is None:
        raise RuntimeError("Failed to load created claim config")
    return claim_config


async def update_claim_config(
    db: AsyncSession,
    *,
    claim_config_id: int,
    counterparty_company_id: UUID | None = None,
    default_submission_channel: enumerations.ClaimSubmissionChannel | None = None,
    default_contact: str | None = None,
    portal_url: str | None = None,
    update_default_contact: bool = False,
    update_portal_url: bool = False,
) -> models.ClaimConfig | None:
    """Patch fields on a claim config.

    Args:
        db: Async DB session.
        claim_config_id: Config to update.
        counterparty_company_id: New OEM company (optional).
        default_submission_channel: New channel (optional).
        default_contact: New contact (optional).
        portal_url: New portal URL (optional).
        update_default_contact: When True, ``default_contact`` (incl. None)
            is applied; when False, ``default_contact`` is ignored.
        update_portal_url: When True, ``portal_url`` (incl. None) is applied;
            when False, ``portal_url`` is ignored.
    """
    values: dict[str, Any] = {}
    if counterparty_company_id is not None:
        values["counterparty_company_id"] = counterparty_company_id
    if default_submission_channel is not None:
        values["default_submission_channel"] = default_submission_channel
    if update_default_contact:
        values["default_contact"] = default_contact
    if update_portal_url:
        values["portal_url"] = portal_url

    if not values:
        claim_config = await claim_config_queries.query_claim_config(
            claim_config_id=claim_config_id,
        ).get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        )
        return cast(models.ClaimConfig | None, claim_config)

    row = await claim_config_queries.query_update_claim_config(
        claim_config_id=claim_config_id,
        values=values,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    updated_claim_config_id = _returned_int(row=row, key="claim_config_id")
    if updated_claim_config_id is None:
        return None
    await db.commit()
    claim_config = await claim_config_queries.query_claim_config(
        claim_config_id=updated_claim_config_id,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    return cast(models.ClaimConfig | None, claim_config)


async def delete_claim_config(
    db: AsyncSession,
    *,
    claim_config_id: int,
) -> bool:
    """Delete a claim config. Returns False if config not found.

    Args:
        db: Async DB session.
        claim_config_id: Config to delete.
    """
    row = await claim_config_queries.query_delete_claim_config(
        claim_config_id=claim_config_id,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    await db.commit()
    return _returned_int(row=row, key="claim_config_id") is not None
