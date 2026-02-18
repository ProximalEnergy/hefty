import { SensorTypeEnum } from '@/api/enumerations'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useMemo } from 'react'
import { useParams } from 'react-router'

interface ACVoltageChartProps {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
}

export const ACVoltageChart = ({ realtimeData }: ACVoltageChartProps) => {
  const { projectId } = useParams<{ projectId: string }>()

  const voltageData = useMemo(() => {
    const voltageAB = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_VOLTAGE_LL_AB,
    )
    const voltageBC = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_VOLTAGE_LL_BC,
    )
    const voltageCA = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_VOLTAGE_LL_CA,
    )

    if (
      !voltageAB ||
      !realtimeData.data?.device_names ||
      realtimeData.data.device_names.length === 0
    ) {
      return []
    }

    return [
      {
        x: realtimeData.data.device_names.filter(
          (n): n is string => n !== null,
        ),
        y: voltageAB.values || [],
        type: 'bar' as const,
        name: 'AB',
        marker: { color: '#e74c3c' },
      },
      ...(voltageBC
        ? [
            {
              x: realtimeData.data.device_names.filter(
                (n): n is string => n !== null,
              ),
              y: voltageBC.values || [],
              type: 'bar' as const,
              name: 'BC',
              marker: { color: '#3498db' },
            },
          ]
        : []),
      ...(voltageCA
        ? [
            {
              x: realtimeData.data.device_names.filter(
                (n): n is string => n !== null,
              ),
              y: voltageCA.values || [],
              type: 'bar' as const,
              name: 'CA',
              marker: { color: '#2ecc71' },
            },
          ]
        : []),
    ]
  }, [realtimeData.data])

  return (
    <CustomCard
      title="AC Voltage"
      style={{ height: '400px' }}
      allowMinimize={true}
      storageKey={`pv-pcs-realtime-ac-voltage-${projectId}`}
    >
      <PlotlyPlot
        data={voltageData}
        layout={{
          uirevision: `ac-voltage-${projectId}`,
          barmode: 'group',
          yaxis: { title: { text: 'Voltage (V)' } },
          xaxis: { title: { text: 'PCS Device' } },
        }}
        isLoading={realtimeData.isLoading}
        error={realtimeData.error}
        noDataMessage="No data available. Required sensor types: PV PCS Voltage LL AB (optional: PV PCS Voltage LL BC, PV PCS Voltage LL CA)"
      />
    </CustomCard>
  )
}
