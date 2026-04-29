"""Unified SES email delivery primitives shared across all email senders.

This module owns:
- SES v2 client creation
- Async non-blocking send via ``asyncio.to_thread``
- Simple HTML email payload building (no attachments)
- Raw MIME email payload building (for attachments)
- Convenience ``send_simple_email`` / ``send_mime_email`` coroutines

Notification-state management (Clerk user lookup, notification rows) lives in
``core.utils.notifications`` and calls :func:`send_email_async` directly.
"""

import asyncio
import logging
import mimetypes
from email.message import EmailMessage
from email.utils import formataddr

import boto3

logger = logging.getLogger(__name__)

_SES_REGION = "us-east-2"


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


def make_ses_client():
    """Return a fresh boto3 SES v2 client.

    Returns:
        boto3 SESv2 client instance.
    """
    return boto3.client("sesv2", region_name=_SES_REGION)


# ---------------------------------------------------------------------------
# Low-level async send
# ---------------------------------------------------------------------------


async def send_email_async(*, email_kwargs: dict) -> None:
    """Send an email via SES v2 in a thread pool to avoid blocking the loop.

    Creates a new SES client on each call (thread-safe; boto3 clients must not
    be shared across threads).

    Args:
        email_kwargs: Dict accepted by ``boto3 sesv2.send_email``.
    """

    def _sync_send() -> None:
        client = make_ses_client()
        client.send_email(**email_kwargs)

    await asyncio.to_thread(_sync_send)


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------


def _format_from(
    *,
    from_address: str,
    display_name: str | None,
) -> str:
    """Return a formatted From address, optionally with a display name.

    Args:
        from_address: Bare email address used as the envelope sender.
        display_name: Optional human-readable name shown in mail clients.

    Returns:
        RFC-2822 formatted From string.
    """
    if display_name:
        return formataddr((display_name.strip(), from_address))
    return from_address


def build_simple_email_kwargs(
    *,
    from_address: str,
    to: list[str],
    subject: str,
    html_body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: list[str] | None = None,
    display_name: str | None = None,
) -> dict:
    """Build SES ``send_email`` kwargs for a simple HTML message (no attachments).

    Args:
        from_address: Envelope sender email address.
        to: List of To recipients.
        subject: Email subject line.
        html_body: Full HTML body string.
        cc: Optional CC recipients.
        bcc: Optional BCC recipients.
        reply_to: Optional Reply-To addresses.
        display_name: Optional display name shown alongside ``from_address``.

    Returns:
        Dict suitable for ``boto3 sesv2.send_email(**kwargs)``.
    """
    from_formatted = _format_from(
        from_address=from_address,
        display_name=display_name,
    )
    destination: dict[str, list[str]] = {"ToAddresses": to}
    if cc:
        destination["CcAddresses"] = cc
    if bcc:
        destination["BccAddresses"] = bcc

    kwargs: dict = {
        "FromEmailAddress": from_formatted,
        "Destination": destination,
        "Content": {
            "Simple": {
                "Subject": {"Data": subject},
                "Body": {"Html": {"Data": html_body}},
            },
        },
    }
    if reply_to:
        kwargs["ReplyToAddresses"] = reply_to
    return kwargs


type EmailAttachment = dict[str, bytes | str | None]


def build_mime_email_kwargs(
    *,
    from_address: str,
    to: list[str],
    subject: str,
    html_body: str,
    attachments: list[EmailAttachment],
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: list[str] | None = None,
    display_name: str | None = None,
) -> dict:
    """Build SES ``send_email`` kwargs for a raw MIME message with attachments.

    Non-bytes or empty attachment content entries are skipped with a warning.

    Args:
        from_address: Envelope sender email address.
        to: List of To recipients.
        subject: Email subject line.
        html_body: Full HTML body string.
        attachments: List of attachment dicts with keys:
            ``filename`` (str), ``content`` (bytes), ``content_type`` (str, optional).
        cc: Optional CC recipients.
        bcc: Optional BCC recipients.
        reply_to: Optional Reply-To addresses.
        display_name: Optional display name shown alongside ``from_address``.

    Returns:
        Dict suitable for ``boto3 sesv2.send_email(**kwargs)``.
    """
    from_formatted = _format_from(
        from_address=from_address,
        display_name=display_name,
    )
    destination: dict[str, list[str]] = {"ToAddresses": to}
    if cc:
        destination["CcAddresses"] = cc
    if bcc:
        destination["BccAddresses"] = bcc

    msg = EmailMessage()
    msg["From"] = from_formatted
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if reply_to:
        msg["Reply-To"] = ", ".join(reply_to)
    msg["Subject"] = subject
    msg.set_content("Please view this email in an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")

    for attachment in attachments:
        filename = str(attachment.get("filename") or "attachment")
        content = attachment.get("content")
        if content is None or content == b"":
            continue
        if not isinstance(content, bytes):
            logger.warning("Skipping non-bytes email attachment: %s", filename)
            continue
        content_type = str(attachment.get("content_type") or "")
        guessed = mimetypes.guess_type(filename)[0]
        resolved = content_type or guessed or "application/octet-stream"
        maintype, subtype = resolved.split("/", 1)
        msg.add_attachment(
            content,
            maintype=maintype,
            subtype=subtype,
            filename=filename,
        )

    kwargs: dict = {
        "FromEmailAddress": from_formatted,
        "Destination": destination,
        "Content": {"Raw": {"Data": msg.as_bytes()}},
    }
    if reply_to:
        kwargs["ReplyToAddresses"] = reply_to
    return kwargs


# ---------------------------------------------------------------------------
# Convenience coroutines
# ---------------------------------------------------------------------------


async def send_simple_email(
    *,
    from_address: str,
    to: list[str],
    subject: str,
    html_body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: list[str] | None = None,
    display_name: str | None = None,
) -> None:
    """Build and send a simple HTML email (no attachments) via SES.

    Args:
        from_address: Envelope sender email address.
        to: List of To recipients.
        subject: Email subject line.
        html_body: Full HTML body string.
        cc: Optional CC recipients.
        bcc: Optional BCC recipients.
        reply_to: Optional Reply-To addresses.
        display_name: Optional display name shown alongside ``from_address``.
    """
    kwargs = build_simple_email_kwargs(
        from_address=from_address,
        to=to,
        subject=subject,
        html_body=html_body,
        cc=cc,
        bcc=bcc,
        reply_to=reply_to,
        display_name=display_name,
    )
    await send_email_async(email_kwargs=kwargs)


async def send_mime_email(
    *,
    from_address: str,
    to: list[str],
    subject: str,
    html_body: str,
    attachments: list[EmailAttachment],
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: list[str] | None = None,
    display_name: str | None = None,
) -> None:
    """Build and send a MIME email with attachments via SES.

    Args:
        from_address: Envelope sender email address.
        to: List of To recipients.
        subject: Email subject line.
        html_body: Full HTML body string.
        attachments: List of attachment dicts (see :func:`build_mime_email_kwargs`).
        cc: Optional CC recipients.
        bcc: Optional BCC recipients.
        reply_to: Optional Reply-To addresses.
        display_name: Optional display name shown alongside ``from_address``.
    """
    kwargs = build_mime_email_kwargs(
        from_address=from_address,
        to=to,
        subject=subject,
        html_body=html_body,
        attachments=attachments,
        cc=cc,
        bcc=bcc,
        reply_to=reply_to,
        display_name=display_name,
    )
    await send_email_async(email_kwargs=kwargs)
