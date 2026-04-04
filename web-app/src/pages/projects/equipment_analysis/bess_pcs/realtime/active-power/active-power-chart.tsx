import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import { ActivePowerChart as SharedActivePowerChart } from '@/components/bess-pcs/ActivePowerChart'

type ActivePowerChartProps = {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
  maxCapacityMWac: number | null
}

export function ActivePowerChart({
  realtimeData,
  maxCapacityMWac,
}: ActivePowerChartProps) {
  return (
    <SharedActivePowerChart
      realtimeData={realtimeData}
      maxCapacityMWac={maxCapacityMWac}
    />
  )
}
