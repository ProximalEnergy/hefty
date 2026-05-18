export function colorFromPercent(
  numerator: number,
  denominator: number,
): string {
  const percent = (numerator / denominator) * 100

  if (percent >= 90) {
    return 'green'
  }

  if (percent >= 75) {
    return 'yellow'
  }

  return 'red'
}
