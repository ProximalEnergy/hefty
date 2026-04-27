import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import { DCVoltageChartBessPcs } from '@/components/bess-pcs/DCVoltageChart'

type DCVoltageChartProps = {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
}

export function DCVoltageChartBessPcsRealtime({
  realtimeData,
}: DCVoltageChartProps) {
  return <DCVoltageChartBessPcs realtimeData={realtimeData} />
}
