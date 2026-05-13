/**
 * Save a Blob in the browser using a temporary object URL.
 */
function triggerDownloadFromBlob(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

/** Download a file that exists only in the browser (not yet uploaded). */
export function triggerDownloadFromLocalFile(file: File): void {
  triggerDownloadFromBlob(file, file.name)
}

/**
 * Download a remote URL as ``filename``. Tries fetch + blob first; if that
 * fails (e.g. CORS), opens the URL in a new tab so the user can save manually.
 */
export async function downloadRemoteFileBestEffort(
  url: string,
  filename: string,
): Promise<void> {
  try {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const blob = await response.blob()
    triggerDownloadFromBlob(blob, filename)
  } catch {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}
