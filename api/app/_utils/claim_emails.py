"""Email sending for warranty claim submissions."""

import html
import logging

from core.utils.email_delivery import (
    EmailAttachment,
    send_mime_email,
    send_simple_email,
)

logger = logging.getLogger(__name__)

FROM_ADDRESS = "support@proximal.energy"
PROXIMAL_BLUE = "#00AEEF"


def plain_text_email_to_html(*, text: str) -> str:
    """Turn plain text (paragraphs separated by blank lines) into simple HTML.

    Args:
        text: User-authored message body.

    Returns:
        HTML fragment safe for email bodies.
    """
    chunks: list[str] = []
    for block in text.strip().split("\n\n"):
        block_stripped = block.strip()
        if not block_stripped:
            continue
        inner = "<br />\n".join(
            html.escape(line) for line in block_stripped.split("\n")
        )
        chunks.append(f"<p>{inner}</p>")
    return "\n".join(chunks) if chunks else "<p></p>"


def build_claim_submission_email_html(
    *,
    text: str,
    project_name: str,
    claim_id: int,
    counterparty_name: str,
    sender_company: str,
    attachment_filenames: list[str] | None = None,
) -> str:
    """Build branded HTML for a warranty claim submission email.

    Args:
        text: User-authored message body.
        project_name: Project name for email context.
        claim_id: Claim id being submitted.
        counterparty_name: OEM / counterparty name.
        sender_company: Company submitting the claim.
        attachment_filenames: Names of files attached to the outbound email.

    Returns:
        Full HTML email document.
    """
    body_html = plain_text_email_to_html(text=text)
    safe_project_name = html.escape(project_name)
    safe_counterparty_name = html.escape(counterparty_name)
    safe_sender_company = html.escape(sender_company or "Your Company")
    safe_claim_id = html.escape(str(claim_id))
    safe_attachment_names = [
        html.escape(filename)
        for filename in (attachment_filenames or [])
        if filename.strip()
    ]
    attachment_rows = "\n                    ".join(
        f"<li>{filename}</li>" for filename in safe_attachment_names
    )
    attachments_html = (
        f"""<tr>
              <td style="padding:0 28px 28px 28px;">
                <div style="border-top:1px solid #e9ecef;padding-top:18px;">
                  <div style="font-size:13px;font-weight:700;color:#1a1b1e;
                    margin-bottom:10px;">Attachments</div>
                  <ul style="margin:0;padding-left:20px;color:#495057;
                    font-size:13px;line-height:1.6;">
                    {attachment_rows}
                  </ul>
                </div>
              </td>
            </tr>"""
        if safe_attachment_names
        else ""
    )
    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f8f9fa;">
    <div style="display:none;max-height:0;overflow:hidden;color:transparent;">
      Warranty claim #{safe_claim_id} for {safe_project_name}
    </div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
      style="background:#f8f9fa;padding:28px 12px;font-family:-apple-system,
      BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;color:#1a1b1e;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
            style="max-width:680px;background:#ffffff;border:1px solid #e9ecef;
            border-radius:16px;overflow:hidden;box-shadow:0 8px 24px
            rgba(15,23,42,0.08);">
            <tr>
              <td style="background:{PROXIMAL_BLUE};padding:22px 28px;">
                <div style="font-size:13px;font-weight:700;letter-spacing:.08em;
                  text-transform:uppercase;color:#e7f8ff;">{safe_sender_company}</div>
                <div style="margin-top:8px;font-size:26px;line-height:1.25;
                  font-weight:800;color:#ffffff;">Warranty Claim Submission</div>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 28px 10px 28px;">
                <table role="presentation" width="100%" cellspacing="0"
                  cellpadding="0" style="border-collapse:separate;
                  border-spacing:0 8px;">
                  <tr>
                    <td style="width:120px;color:#868e96;font-size:13px;">
                      Claim
                    </td>
                    <td style="font-size:14px;font-weight:700;color:#1a1b1e;">
                      #{safe_claim_id}
                    </td>
                  </tr>
                  <tr>
                    <td style="width:120px;color:#868e96;font-size:13px;">
                      Project
                    </td>
                    <td style="font-size:14px;font-weight:700;color:#1a1b1e;">
                      {safe_project_name}
                    </td>
                  </tr>
                  <tr>
                    <td style="width:120px;color:#868e96;font-size:13px;">
                      Recipient
                    </td>
                    <td style="font-size:14px;font-weight:700;color:#1a1b1e;">
                      {safe_counterparty_name}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:10px 28px 28px 28px;">
                <div style="border-top:1px solid #e9ecef;padding-top:22px;
                  font-size:15px;line-height:1.65;color:#2f3437;">
                  {body_html}
                </div>
              </td>
            </tr>
            {attachments_html}
            <tr>
              <td style="background:#f1f3f5;padding:18px 28px;color:#6c757d;
                font-size:12px;line-height:1.5;">
                This warranty claim was prepared on behalf of
                {safe_sender_company}. Supporting documents are attached when
                available.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


async def send_claim_submission_email(
    *,
    to_emails: list[str],
    cc_emails: list[str],
    bcc_emails: list[str],
    subject: str,
    html_body: str,
    sender_name: str,
    sender_company: str,
    attachments: list[EmailAttachment] | None = None,
) -> None:
    """Send claim submission notification via SES.

    Args:
        to_emails: OEM / counterparty To recipients (one or more addresses).
        cc_emails: CC recipients.
        bcc_emails: BCC recipients.
        subject: Email subject line.
        html_body: Full HTML body (including outer html/body if desired).
        sender_name: User name shown in the email From display name.
        sender_company: User company shown in the email From display name.
        attachments: Files to attach to the outbound email.
    """
    display_name_parts = [
        part.strip() for part in (sender_name, sender_company) if part and part.strip()
    ]
    display_name = ", ".join(display_name_parts) or None

    if attachments:
        await send_mime_email(
            from_address=FROM_ADDRESS,
            to=to_emails,
            subject=subject,
            html_body=html_body,
            attachments=attachments,
            cc=cc_emails or None,
            bcc=bcc_emails or None,
            display_name=display_name,
        )
    else:
        await send_simple_email(
            from_address=FROM_ADDRESS,
            to=to_emails,
            subject=subject,
            html_body=html_body,
            cc=cc_emails or None,
            bcc=bcc_emails or None,
            display_name=display_name,
        )

    logger.info("Claim submission email sent to %s", ", ".join(to_emails))
