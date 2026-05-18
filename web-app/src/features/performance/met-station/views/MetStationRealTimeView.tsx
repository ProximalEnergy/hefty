import type { MetStationContext } from '../types/met-station'

type MetStationRealTimeViewProps = {
  context: MetStationContext
}

export function MetStationRealTimeView({
  context,
}: MetStationRealTimeViewProps) {
  void context

  return (
    <div>
      <h1>Real Time View</h1>
    </div>
  )
}
