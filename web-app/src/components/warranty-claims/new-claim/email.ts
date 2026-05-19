import type { DeviceEntry } from '@/components/warranty-claims/new-claim/devices'

export const CLAIM_EMAIL_LABEL_COL_W = 76
const PROXIMAL_BLUE = '#00AEEF'

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
}

function plainTextEmailToHtml(text: string): string {
  const chunks = text
    .trim()
    .split('\n\n')
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      const inner = block
        .split('\n')
        .map((line) => escapeHtml(line))
        .join('<br />\n')
      return `<p>${inner}</p>`
    })

  return chunks.length > 0 ? chunks.join('\n') : '<p></p>'
}

/** Comma, space, or semicolon separated; de-duplicated (deal-room style). */
export function parseEmailAddressList(raw: string): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const part of raw.split(/[\s,;]+/)) {
    const e = part.trim()
    if (!e) continue
    const k = e.toLowerCase()
    if (seen.has(k)) continue
    seen.add(k)
    out.push(e)
  }
  return out
}

export function buildDefaultClaimEmailSubject(
  claimId: number | null,
  oemName: string,
  projectName: string,
): string {
  const idPart = claimId != null ? `#${claimId}` : '(pending)'
  return `Warranty Claim ${idPart} — ${oemName} — ${projectName}`
}

export function buildDefaultClaimEmailBody(
  oemName: string,
  projectName: string,
  summary: string,
  devices: DeviceEntry[],
  attachmentCount: number,
  senderName: string,
  senderCompany: string,
): string {
  const paras: string[] = []

  paras.push(
    `Dear ${oemName} Warranty Team,\n\n` +
      `We are writing to formally submit a warranty claim for ` +
      `${projectName}.`,
  )

  if (summary.trim()) {
    paras.push(`Claim summary:\n\n${summary.trim()}`)
  }
  if (devices.length > 0) {
    const lines = devices.map((d) => {
      let line = `• ${d.device_name}`
      if (d.oem_serial_number) {
        line += ` (S/N: ${d.oem_serial_number})`
      }
      if (d.oem_part_number) {
        line += ` (Part: ${d.oem_part_number})`
      }
      if (d.notes) {
        line += ` — ${d.notes}`
      }
      return line
    })
    paras.push(
      `The following ${devices.length} device(s) are affected:\n\n` +
        lines.join('\n'),
    )
  }
  if (attachmentCount > 0) {
    paras.push(
      `We have attached ${attachmentCount} supporting document(s) ` +
        `for your review.`,
    )
  }

  paras.push(
    'We kindly request that you review this claim and provide a response ' +
      'regarding warranty coverage and next steps at your earliest ' +
      'convenience.',
  )
  paras.push(
    'Please do not hesitate to reach out if you require any additional ' +
      'information or documentation.',
  )
  const senderLines = [senderName, senderCompany].filter(Boolean)
  paras.push(`Best regards,\n\n${senderLines.join('\n') || senderCompany}`)

  return paras.join('\n\n')
}

export function buildClaimSubmissionEmailHtml({
  text,
  projectName,
  claimId,
  counterpartyName,
  senderCompany,
  attachmentNames,
  toAddressesDisplay,
}: {
  text: string
  projectName: string
  claimId: number | null
  counterpartyName: string
  senderCompany: string
  attachmentNames: string[]
  /** Shown in preview when set (comma-separated To line). */
  toAddressesDisplay?: string | null
}): string {
  const bodyHtml = plainTextEmailToHtml(text)
  const safeProjectName = escapeHtml(projectName)
  const safeCounterpartyName = escapeHtml(counterpartyName)
  const safeSenderCompany = escapeHtml(senderCompany || 'Your Company')
  const safeClaimId = escapeHtml(claimId != null ? String(claimId) : 'pending')
  const toRowHtml =
    toAddressesDisplay != null && toAddressesDisplay.trim() !== ''
      ? `<tr>
                    <td style="width:120px;color:#868e96;font-size:13px;">
                      To
                    </td>
                    <td style="font-size:14px;font-weight:700;color:#1a1b1e;">
                      ${escapeHtml(toAddressesDisplay.trim())}
                    </td>
                  </tr>`
      : ''

  const attachmentsHtml =
    attachmentNames.length > 0
      ? `<tr>
              <td style="padding:0 28px 28px 28px;">
                <div style="border-top:1px solid #e9ecef;padding-top:18px;">
                  <div style="font-size:13px;font-weight:700;color:#1a1b1e;
                    margin-bottom:10px;">Attachments</div>
                  <ul style="margin:0;padding-left:20px;color:#495057;
                    font-size:13px;line-height:1.6;">
                    ${attachmentNames
                      .map((name) => `<li>${escapeHtml(name)}</li>`)
                      .join('\n                    ')}
                  </ul>
                </div>
              </td>
            </tr>`
      : ''

  return `<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f8f9fa;">
    <div style="display:none;max-height:0;overflow:hidden;color:transparent;">
      Warranty claim #${safeClaimId} for ${safeProjectName}
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
              <td style="background:${PROXIMAL_BLUE};padding:22px 28px;">
                <div style="font-size:13px;font-weight:700;letter-spacing:.08em;
                  text-transform:uppercase;color:#e7f8ff;">${safeSenderCompany}</div>
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
                      #${safeClaimId}
                    </td>
                  </tr>
                  <tr>
                    <td style="width:120px;color:#868e96;font-size:13px;">
                      Project
                    </td>
                    <td style="font-size:14px;font-weight:700;color:#1a1b1e;">
                      ${safeProjectName}
                    </td>
                  </tr>
                  ${toRowHtml}
                  <tr>
                    <td style="width:120px;color:#868e96;font-size:13px;">
                      Recipient
                    </td>
                    <td style="font-size:14px;font-weight:700;color:#1a1b1e;">
                      ${safeCounterpartyName}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:10px 28px 28px 28px;">
                <div style="border-top:1px solid #e9ecef;padding-top:22px;
                  font-size:15px;line-height:1.65;color:#2f3437;">
                  ${bodyHtml}
                </div>
              </td>
            </tr>
            ${attachmentsHtml}
            <tr>
              <td style="background:#f1f3f5;padding:18px 28px;color:#6c757d;
                font-size:12px;line-height:1.5;">
                This warranty claim was prepared on behalf of
                ${safeSenderCompany}. Supporting documents are attached when
                available.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>`
}
