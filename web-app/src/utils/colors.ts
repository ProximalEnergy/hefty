import chroma from 'chroma-js'

/**
 * Sorts devices naturally by name and assigns a color to each device
 * from a gradient scale to differentiate low number devices from high number devices.
 *
 * @param devices Array of device objects with a name property
 * @returns Array of devices sorted by name with an assigned color property
 */
export const sortAndColorDevices = <T extends { name: string }>(
  devices: T[],
): (T & { color: string })[] => {
  // Sort devices naturally (e.g. "Device 1", "Device 2", "Device 10")
  const sortedDevices = [...devices].sort((a, b) =>
    a.name.localeCompare(b.name, undefined, {
      numeric: true,
      sensitivity: 'base',
    }),
  )

  const count = sortedDevices.length
  if (count === 0) return []

  // Create a color scale
  // Using 'Spectral' (Red-Yellow-Blue-ish) provides good differentiation
  // We assign a color based on the device's sorted position
  const scale = chroma.scale('Spectral')

  return sortedDevices.map((device, index) => {
    // Calculate position from 0 to 1
    const position = count > 1 ? index / (count - 1) : 0
    return {
      ...device,
      color: scale(position).hex(),
    }
  })
}
