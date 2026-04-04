import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import { DCVoltageChart as SharedDCVoltageChart } from '@/components/bess-pcs/DCVoltageChart'

type DCVoltageChartProps = {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
}

export function DCVoltageChart({ realtimeData }: DCVoltageChartProps) {
  return <SharedDCVoltageChart realtimeData={realtimeData} />
}
