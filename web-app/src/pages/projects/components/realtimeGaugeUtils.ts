export const getRealtimeGaugeColor = (
  pct: number,
): 'green' | 'yellow' | 'red' => {
  if (pct >= 90) return 'green'
  if (pct >= 70) return 'yellow'
  return 'red'
}
