/** Centered moving average; skips non‑finite values within each window. */
export const calculateMovingAverage = (
  data: Array<number | null | string>,
  windowSize: number,
): Array<number | null> => {
  if (data.length === 0) return []

  const result: Array<number | null> = []
  const halfWindow = Math.floor(windowSize / 2)

  for (let i = 0; i < data.length; i += 1) {
    const start = Math.max(0, i - halfWindow)
    const end = Math.min(data.length, i + halfWindow + 1)
    const window = data.slice(start, end)
    const numericValues = window
      .map((value) => {
        if (typeof value === 'number') return value
        if (typeof value === 'string') return Number(value)
        return null
      })
      .filter((value): value is number => Number.isFinite(value))
    if (numericValues.length === 0) {
      result.push(null)
      continue
    }
    const average =
      numericValues.reduce((sum, val) => sum + val, 0) / numericValues.length
    result.push(average)
  }

  return result
}
