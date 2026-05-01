from typing import Any, Literal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from core import models
from core.db_query import DbQuery


def get_claim_attachment(
    *,
    claim_id: int,
    filename: str,
) -> DbQuery[models.ClaimAttachment, Literal[True]]:
    """Build a query for one claim attachment metadata row.

    Args:
        claim_id: Parent claim id.
        filename: Attachment filename.
    """
    stmt = sa.select(models.ClaimAttachment).where(
        models.ClaimAttachment.claim_id == claim_id,
        models.ClaimAttachment.filename == filename,
    )
    return DbQuery(query=stmt, is_scalar=True)


def query_claim_attachments(
    *,
    claim_id: int,
) -> DbQuery[models.ClaimAttachment, Literal[False]]:
    """Build a query for claim attachment metadata rows.

    Args:
        claim_id: Parent claim id.
    """
    stmt = (
        sa.select(models.ClaimAttachment)
        .where(models.ClaimAttachment.claim_id == claim_id)
        .order_by(
            models.ClaimAttachment.uploaded_at,
            models.ClaimAttachment.claim_attachment_id,
        )
    )
    return DbQuery(query=stmt)


def upsert_claim_attachment(
    *,
    claim_id: int,
    filename: str,
    s3_key: str,
    content_type: str | None,
    claim_update_id: int | None,
) -> DbQuery[Any, Literal[False]]:
    """Build an upsert for claim attachment metadata.

    Args:
        claim_id: Parent claim id.
        filename: Original attachment filename.
        s3_key: S3 object key.
        content_type: MIME type, if known.
        claim_update_id: Optional update entry linked to the attachment.
    """
    stmt = insert(models.ClaimAttachment).values(
        claim_id=claim_id,
        filename=filename,
        s3_key=s3_key,
        content_type=content_type,
        claim_update_id=claim_update_id,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_claim_attachments_claim_filename",
        set_={
            "s3_key": stmt.excluded.s3_key,
            "content_type": stmt.excluded.content_type,
            "claim_update_id": stmt.excluded.claim_update_id,
            "uploaded_at": sa.func.now(),
        },
    )
    return DbQuery(query=stmt)


def delete_claim_attachment_metadata(
    *,
    claim_id: int,
    filename: str,
) -> DbQuery[Any, Literal[False]]:
    """Build a delete for one claim attachment metadata row.

    Args:
        claim_id: Parent claim id.
        filename: Attachment filename.
    """
    stmt = sa.delete(models.ClaimAttachment).where(
        models.ClaimAttachment.claim_id == claim_id,
        models.ClaimAttachment.filename == filename,
    )
    return DbQuery(query=stmt)


def delete_claim_attachments_metadata(
    *,
    claim_id: int,
) -> DbQuery[Any, Literal[False]]:
    """Build a delete for all attachment metadata rows on a claim.

    Args:
        claim_id: Parent claim id.
    """
    stmt = sa.delete(models.ClaimAttachment).where(
        models.ClaimAttachment.claim_id == claim_id
    )
    return DbQuery(query=stmt)
