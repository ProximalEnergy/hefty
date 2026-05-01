"""S3-backed file storage with DB-backed claim attachment metadata."""

import logging
from typing import Any, cast

import boto3
from botocore.exceptions import ClientError
from core.crud.project import claim_attachments as claim_attachment_queries
from core.db_query import OutputType
from sqlalchemy.ext.asyncio import AsyncSession

from core import models

BUCKET_NAME = "proximal-am-documents"
REGION_NAME = "us-east-2"

logger = logging.getLogger(__name__)


def _attachment_key(
    *,
    project_schema: str,
    claim_id: int,
    filename: str,
) -> str:
    """S3 key for an individual attachment file.

    Args:
        project_schema: Project schema name.
        claim_id: Claim id.
        filename: Original filename.
    """
    return f"claims/{project_schema}/{claim_id}/{filename}"


def _presigned_url(*, s3_key: str) -> str:
    """Generate a presigned GET URL.

    Args:
        s3_key: S3 object key.
    """
    s3 = boto3.client("s3", region_name=REGION_NAME)
    return str(
        s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": s3_key,
            },
            ExpiresIn=3600,
        )
    )


def _attachment_to_dict(
    *,
    attachment: models.ClaimAttachment,
    include_url: bool = True,
) -> dict[str, Any]:
    """Convert an attachment model into the API response shape.

    Args:
        attachment: Attachment metadata row.
        include_url: Whether to include a presigned download URL.
    """
    uploaded_at = attachment.uploaded_at
    row: dict[str, Any] = {
        "claim_id": attachment.claim_id,
        "s3_key": attachment.s3_key,
        "filename": attachment.filename,
        "content_type": attachment.content_type,
        "uploaded_at": uploaded_at.isoformat() if uploaded_at else None,
        "claim_update_id": attachment.claim_update_id,
    }
    if include_url:
        row["url"] = _presigned_url(s3_key=attachment.s3_key)
    return row


async def _get_claim_attachment(
    *,
    db: AsyncSession,
    claim_id: int,
    filename: str,
) -> models.ClaimAttachment | None:
    """Fetch one attachment metadata row.

    Args:
        db: Project-scoped DB session.
        claim_id: Parent claim id.
        filename: Attachment filename.
    """
    attachment = await claim_attachment_queries.get_claim_attachment(
        claim_id=claim_id,
        filename=filename,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    return cast(models.ClaimAttachment | None, attachment)


async def _list_claim_attachment_models(
    *,
    db: AsyncSession,
    claim_id: int,
) -> list[models.ClaimAttachment]:
    """Fetch claim attachment metadata rows.

    Args:
        db: Project-scoped DB session.
        claim_id: Parent claim id.
    """
    attachments = await claim_attachment_queries.query_claim_attachments(
        claim_id=claim_id,
    ).get_async(
        executor=db,
        output_type=OutputType.SQLALCHEMY,
    )
    return cast(
        list[models.ClaimAttachment],
        attachments,
    )


async def get_claim_attachments(
    *,
    db: AsyncSession,
    claim_id: int,
) -> list[dict[str, Any]]:
    """List attachments for a claim.

    Args:
        db: Project-scoped DB session.
        claim_id: Claim to filter by.
    """
    return [
        _attachment_to_dict(attachment=attachment)
        for attachment in await _list_claim_attachment_models(
            db=db,
            claim_id=claim_id,
        )
    ]


async def get_claim_attachment_files(
    *,
    db: AsyncSession,
    claim_id: int,
) -> list[dict[str, Any]]:
    """Fetch attachment file contents for a claim.

    Args:
        db: Project-scoped DB session.
        claim_id: Claim to filter by.
    """
    s3 = boto3.client("s3", region_name=REGION_NAME)
    files = []
    attachments = await _list_claim_attachment_models(
        db=db,
        claim_id=claim_id,
    )
    for attachment in attachments:
        resp = s3.get_object(Bucket=BUCKET_NAME, Key=attachment.s3_key)
        files.append(
            {
                "filename": attachment.filename,
                "content_type": attachment.content_type,
                "content": resp["Body"].read(),
            }
        )
    return files


async def add_claim_attachment(
    *,
    db: AsyncSession,
    project_schema: str,
    claim_id: int,
    filename: str,
    file_content: bytes,
    content_type: str | None = None,
    claim_update_id: int | None = None,
) -> dict[str, Any]:
    """Upload a file to S3 and record its metadata in the database.

    Args:
        db: Project-scoped DB session.
        project_schema: Project schema name.
        claim_id: Parent claim id.
        filename: Original filename.
        file_content: Raw file bytes.
        content_type: MIME type.
        claim_update_id: Optional update entry to associate with the attachment.
    """
    s3 = boto3.client("s3", region_name=REGION_NAME)
    s3_key = _attachment_key(
        project_schema=project_schema,
        claim_id=claim_id,
        filename=filename,
    )

    put_kwargs: dict[str, Any] = {
        "Bucket": BUCKET_NAME,
        "Key": s3_key,
        "Body": file_content,
    }
    if content_type:
        put_kwargs["ContentType"] = content_type
    s3.put_object(**put_kwargs)

    await claim_attachment_queries.upsert_claim_attachment(
        claim_id=claim_id,
        filename=filename,
        s3_key=s3_key,
        content_type=content_type,
        claim_update_id=claim_update_id,
    ).execute_async(
        executor=db,
    )
    await db.commit()
    attachment = await _get_claim_attachment(
        db=db,
        claim_id=claim_id,
        filename=filename,
    )
    if attachment is None:
        raise RuntimeError("Failed to load claim attachment")
    return _attachment_to_dict(attachment=attachment)


async def delete_claim_attachment(
    *,
    db: AsyncSession,
    claim_id: int,
    filename: str,
) -> bool:
    """Remove an attachment file and its DB metadata row.

    Args:
        db: Project-scoped DB session.
        claim_id: Claim id.
        filename: Filename to delete.
    """
    attachment = await _get_claim_attachment(
        db=db,
        claim_id=claim_id,
        filename=filename,
    )
    if attachment is None:
        return False

    s3 = boto3.client("s3", region_name=REGION_NAME)
    try:
        s3.delete_object(Bucket=BUCKET_NAME, Key=attachment.s3_key)
    except ClientError:
        logger.warning(
            "Failed to delete S3 object %s",
            attachment.s3_key,
            exc_info=True,
        )

    await claim_attachment_queries.delete_claim_attachment_metadata(
        claim_id=claim_id,
        filename=filename,
    ).execute_async(
        executor=db,
    )
    await db.commit()
    return True
