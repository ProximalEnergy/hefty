import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import { BessPcsReactivePowerChart } from '@/components/bess-pcs/ReactivePowerChart'

type BessPcsRealtimeReactivePowerChartProps = {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
  maxCapacityMWac: number | null
}

export function BessPcsRealtimeReactivePowerChart({
  realtimeData,
  maxCapacityMWac,
}: BessPcsRealtimeReactivePowerChartProps) {
  return (
    <BessPcsReactivePowerChart
      realtimeData={realtimeData}
      maxCapacityMWac={maxCapacityMWac}
    />
  )
}
