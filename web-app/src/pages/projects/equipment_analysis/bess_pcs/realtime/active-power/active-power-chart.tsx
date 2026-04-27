import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import { ActivePowerChartBessPcs } from '@/components/bess-pcs/ActivePowerChart'

type ActivePowerChartProps = {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
  maxCapacityMWac: number | null
}

export function ActivePowerChartBessPcsRealtime({
  realtimeData,
  maxCapacityMWac,
}: ActivePowerChartProps) {
  return (
    <ActivePowerChartBessPcs
      realtimeData={realtimeData}
      maxCapacityMWac={maxCapacityMWac}
    />
  )
}
