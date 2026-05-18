import type { MetStationContext } from '../types/met-station'

type MetStationLongTermViewProps = {
  context: MetStationContext
}

export function MetStationLongTermView({
  context,
}: MetStationLongTermViewProps) {
  void context

  return (
    <div>
      <h1>Long Term View</h1>
    </div>
  )
}
