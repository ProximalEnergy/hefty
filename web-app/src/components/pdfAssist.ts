import { PDFDocument } from 'pdf-lib'

export async function extractPdfAcroFormFilledFieldsForAssist(
  fileUrl: string,
  {
    maxChars,
  }: {
    maxChars: number
  },
): Promise<string> {
  const resp = await fetch(fileUrl)
  if (!resp.ok) throw new Error('Failed to fetch PDF')
  const bytes = new Uint8Array(await resp.arrayBuffer())
  const doc = await PDFDocument.load(bytes.slice(), {
    ignoreEncryption: true,
  })
  const form = doc.getForm()
  const lines: string[] = []

  for (const field of form.getFields()) {
    const fieldName = field.getName().trim()
    if (!fieldName) continue

    let value = ''
    try {
      value = form.getTextField(fieldName).getText()?.trim() ?? ''
    } catch {
      /* only text fields are useful as prior filled-form examples */
    }
    if (!value) continue

    lines.push(`${fieldName}: ${value.replace(/\s+/g, ' ')}`)
    if (lines.join('\n').length >= maxChars) break
  }

  return lines.join('\n').slice(0, maxChars)
}
