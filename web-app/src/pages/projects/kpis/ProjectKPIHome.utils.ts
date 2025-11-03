export const getKPIThresholdbyDate = (
  thresholdData: {
    values?: { [key: string]: number }
  } | null,
  date?: Date,
  mode: 'discrete' | 'interpolate' = 'discrete',
): number | null => {
  if (!thresholdData?.values) return null

  const targetDate = date || new Date()
  const targetTime = targetDate.getTime()

  // Convert all dates to timestamps and sort them
  const dates = Object.keys(thresholdData.values)
    .map((dateStr) => new Date(dateStr).getTime())
    .sort((a, b) => a - b)

  if (mode === 'discrete') {
    // Find the most recent date that's before or equal to the target date
    const mostRecentDate = dates
      .filter((timestamp) => timestamp <= targetTime)
      .pop()

    if (mostRecentDate) {
      // Convert back to ISO string format to lookup in thresholdData
      const dateStr = new Date(mostRecentDate).toISOString().split('T')[0]
      return thresholdData.values[dateStr]
    }

    // If no valid date found, use the earliest available threshold
    const earliestDateStr = new Date(dates[0]).toISOString().split('T')[0]
    return thresholdData.values[earliestDateStr] || null
  } else {
    // Interpolation mode
    const beforeDate = dates
      .filter((timestamp) => timestamp <= targetTime)
      .pop()
    const afterDate = dates
      .filter((timestamp) => timestamp > targetTime)
      .shift()

    // If target date is before all threshold dates, return earliest threshold
    if (!beforeDate) {
      const earliestDateStr = new Date(dates[0]).toISOString().split('T')[0]
      return thresholdData.values[earliestDateStr] || null
    }

    // If target date is after all threshold dates, return latest threshold
    if (!afterDate) {
      const latestDateStr = new Date(dates[dates.length - 1])
        .toISOString()
        .split('T')[0]
      return thresholdData.values[latestDateStr] || null
    }

    // Perform linear interpolation
    const beforeDateStr = new Date(beforeDate).toISOString().split('T')[0]
    const afterDateStr = new Date(afterDate).toISOString().split('T')[0]
    const beforeValue = thresholdData.values[beforeDateStr]
    const afterValue = thresholdData.values[afterDateStr]

    const timeFraction = (targetTime - beforeDate) / (afterDate - beforeDate)
    return beforeValue + (afterValue - beforeValue) * timeFraction
  }
}
