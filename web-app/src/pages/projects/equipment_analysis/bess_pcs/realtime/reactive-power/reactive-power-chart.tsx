import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import { ReactivePowerChart as SharedReactivePowerChart } from '@/components/bess-pcs/ReactivePowerChart'

type ReactivePowerChartProps = {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
  maxCapacityMWac: number | null
}

export function ReactivePowerChart({
  realtimeData,
  maxCapacityMWac,
}: ReactivePowerChartProps) {
  return (
    <SharedReactivePowerChart
      realtimeData={realtimeData}
      maxCapacityMWac={maxCapacityMWac}
    />
  )
}
