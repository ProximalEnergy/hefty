import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import type { PlotRelayoutEvent } from 'plotly.js'
import { useMemo, useState } from 'react'
import { useParams } from 'react-router'

const PV_INVERTER_MODULE_DEVICE_TYPE_ID = DeviceTypeEnum.PV_INVERTER_MODULE

interface DCVoltageChartProps {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
}

export const DCVoltageChart = ({ realtimeData }: DCVoltageChartProps) => {
  const { projectId } = useParams<{ projectId: string }>()

  const moduleRealtimeData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: PV_INVERTER_MODULE_DEVICE_TYPE_ID,
    },
    queryParams: {
      sensor_type_ids: [SensorTypeEnum.PV_INVERTER_MODULE_DC_VOLTAGE],
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000,
      staleTime: 15000,
    },
  })

  const [userZoomed, setUserZoomed] = useState(false)
  const [yAxisRange, setYAxisRange] = useState<[number, number] | null>(null)
  const [xAxisRange, setXAxisRange] = useState<[number, number] | null>(null)

  const dcVoltageData = useMemo(() => {
    const pcsDcVoltageTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_DC_VOLTAGE,
    )

    if (
      pcsDcVoltageTrace &&
      realtimeData.data?.device_names &&
      realtimeData.data.device_names.length > 0
    ) {
      const deviceNames = realtimeData.data.device_names.filter(
        (n): n is string => n !== null,
      )
      const dcVoltageValues =
        pcsDcVoltageTrace.values?.map((v) => (v !== null ? v : 0)) || []

      return {
        data: [
          {
            x: deviceNames,
            y: dcVoltageValues,
            type: 'bar' as const,
            name: 'DC Voltage',
            marker: { color: '#f39c12' },
          },
        ],
        isModuleLevel: false,
      }
    }

    const moduleDcVoltageTrace = moduleRealtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_MODULE_DC_VOLTAGE,
    )

    if (
      moduleDcVoltageTrace &&
      moduleRealtimeData.data?.device_names &&
      moduleRealtimeData.data.device_names.length > 0
    ) {
      const deviceNames = moduleRealtimeData.data.device_names.filter(
        (n): n is string => n !== null,
      )
      const dcVoltageValues =
        moduleDcVoltageTrace.values?.map((v) => (v !== null ? v : 0)) || []

      return {
        data: [
          {
            x: deviceNames,
            y: dcVoltageValues,
            type: 'bar' as const,
            name: 'DC Voltage',
            marker: { color: '#f39c12' },
          },
        ],
        isModuleLevel: true,
      }
    }

    return { data: [], isModuleLevel: false }
  }, [realtimeData.data, moduleRealtimeData.data])

  const yAxisRangeComputed = useMemo(() => {
    if (dcVoltageData.data.length === 0) return undefined

    const dcVoltageValues = dcVoltageData.data[0]?.y as number[] | undefined
    if (!dcVoltageValues || dcVoltageValues.length === 0)
      return [0, 100] as [number, number]

    const maxValue = Math.max(
      ...dcVoltageValues.filter((v) => v !== null && v !== undefined),
    )
    const minValue = Math.min(
      0,
      ...dcVoltageValues.filter((v) => v !== null && v !== undefined),
    )

    const yMax = Math.max(100, maxValue * 1.1)
    const yMin = Math.min(0, minValue * 1.1)

    return [yMin, yMax] as [number, number]
  }, [dcVoltageData.data])

  const handleRelayout = (event: Readonly<PlotRelayoutEvent>) => {
    let userZoomedLocal = false

    if (
      event['yaxis.range[0]'] !== undefined &&
      event['yaxis.range[1]'] !== undefined
    ) {
      const newRange: [number, number] = [
        event['yaxis.range[0]'] as number,
        event['yaxis.range[1]'] as number,
      ]
      setYAxisRange(newRange)
      userZoomedLocal = true
    } else if (event['yaxis.autorange'] === true) {
      setYAxisRange(null)
    }

    if (
      event['xaxis.range[0]'] !== undefined &&
      event['xaxis.range[1]'] !== undefined
    ) {
      const newRange: [number, number] = [
        event['xaxis.range[0]'] as number,
        event['xaxis.range[1]'] as number,
      ]
      setXAxisRange(newRange)
      userZoomedLocal = true
    } else if (event['xaxis.autorange'] === true) {
      setXAxisRange(null)
    }

    if (
      event['yaxis.autorange'] === true &&
      event['xaxis.autorange'] === true
    ) {
      setUserZoomed(false)
    } else if (userZoomedLocal) {
      setUserZoomed(true)
    }
  }

  return (
    <CustomCard
      title="DC Voltage"
      style={{ height: '400px' }}
      allowMinimize={true}
      storageKey={`pv-pcs-realtime-dc-voltage-${projectId}`}
    >
      <PlotlyPlot
        data={dcVoltageData.data}
        layout={{
          uirevision: `dc-voltage-${projectId}`,
          yaxis: {
            title: { text: 'Voltage (V)' },
            range: userZoomed && yAxisRange ? yAxisRange : yAxisRangeComputed,
          },
          xaxis: {
            title: {
              text: dcVoltageData.isModuleLevel
                ? 'PCS Module Device'
                : 'PCS Device',
            },
            range: userZoomed && xAxisRange ? xAxisRange : undefined,
          },
        }}
        onRelayout={handleRelayout}
        isLoading={
          dcVoltageData.isModuleLevel
            ? moduleRealtimeData.isLoading
            : realtimeData.isLoading
        }
        error={
          dcVoltageData.isModuleLevel
            ? moduleRealtimeData.error
            : realtimeData.error
        }
        noDataMessage="No data available. Required sensor types: PV Inverter DC Voltage, PV Inverter Module DC Voltage"
      />
    </CustomCard>
  )
}
