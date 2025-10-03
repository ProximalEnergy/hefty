export const linearRegression = (x: number[], y: number[]) => {
  const n = x.length
  const sum_x = x.reduce((a, b) => a + b, 0)
  const sum_y = y.reduce((a, b) => a + b, 0)
  const sum_xy = x.reduce((sum, xi, idx) => sum + xi * y[idx], 0)
  const sum_xx = x.reduce((sum, xi) => sum + xi * xi, 0)

  const denominator = n * sum_xx - sum_x * sum_x
  if (denominator === 0) {
    throw new Error('Cannot perform linear regression: denominator is zero.')
  }

  const slope = (n * sum_xy - sum_x * sum_y) / denominator
  const intercept = (sum_y - slope * sum_x) / n

  return { slope, intercept }
}
