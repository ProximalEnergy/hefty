/**
 * CDN utility functions for generating asset URLs
 */

/**
 * Get the CDN base URL from environment variables
 * Falls back to empty string (relative path) if not configured
 */
function getCdnBaseUrl(): string {
  const cdnUrl = import.meta.env.VITE_CDN_BASE_URL
  if (cdnUrl && typeof cdnUrl === 'string') {
    // Ensure URL doesn't end with a slash
    return cdnUrl.replace(/\/$/, '')
  }
  return ''
}

/**
 * Generate a CDN URL for a device model image
 * @param deviceModelId - The device model ID
 * @returns The full CDN URL or relative path if CDN is not configured
 */
export function getDeviceModelImageUrl(deviceModelId: number | null): string {
  if (deviceModelId === null) {
    return ''
  }

  const cdnBaseUrl = getCdnBaseUrl()
  const imagePath = `/device_models/${deviceModelId}.png`

  if (cdnBaseUrl) {
    return `${cdnBaseUrl}${imagePath}`
  }

  // Fallback to relative path (current behavior)
  return imagePath
}

/**
 * Generate a public (non-CDN) URL for a device model image.
 * Useful as a fallback when CDN images are unavailable.
 * @param deviceModelId - The device model ID
 * @returns The public URL or empty string if no ID
 */
export function getDeviceModelImagePublicUrl(
  deviceModelId: number | null,
): string {
  if (deviceModelId === null) {
    return ''
  }

  return `/device_models/${deviceModelId}.png`
}

/**
 * Generate a CDN URL for a public asset
 * @param assetPath - The asset path relative to public folder (e.g., '/icon_pv_pcs.svg')
 * @returns The full CDN URL or relative path if CDN is not configured
 */
export function getPublicAssetUrl(assetPath: string): string {
  if (!assetPath) {
    return ''
  }

  // Ensure path starts with /
  const normalizedPath = assetPath.startsWith('/') ? assetPath : `/${assetPath}`

  const cdnBaseUrl = getCdnBaseUrl()

  if (cdnBaseUrl) {
    return `${cdnBaseUrl}${normalizedPath}`
  }

  // Fallback to relative path (current behavior)
  return normalizedPath
}

/**
 * Generate a CDN URL for a company logo
 * @param logoFilename - The logo filename (e.g., 'logo_acme.svg')
 * @returns The full CDN URL or relative path if CDN is not configured
 */
export function getCompanyLogoUrl(logoFilename: string): string {
  if (!logoFilename) {
    return ''
  }

  const normalizedName = logoFilename.replace(/^\/+/, '')
  const cdnBaseUrl = getCdnBaseUrl()

  if (cdnBaseUrl) {
    return `${cdnBaseUrl}/company-logos/${normalizedName}`
  }

  // Fallback to public folder (current behavior)
  return `/${normalizedName}`
}
