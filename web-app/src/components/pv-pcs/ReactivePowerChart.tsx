import { SensorTypeEnum } from '@/api/enumerations'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import type { Data, PlotRelayoutEvent } from 'plotly.js'
import { useMemo, useState } from 'react'
import { useParams } from 'react-router'

interface ReactivePowerChartProps {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
  maxCapacityMWac: number | null
}

export const ReactivePowerChart = ({
  realtimeData,
  maxCapacityMWac,
}: ReactivePowerChartProps) => {
  const { projectId } = useParams<{ projectId: string }>()

  const [userZoomed, setUserZoomed] = useState(false)
  const [yAxisRange, setYAxisRange] = useState<[number, number] | null>(null)
  const [xAxisRange, setXAxisRange] = useState<[number, number] | null>(null)

  const reactivePowerChartData = useMemo(() => {
    const reactiveTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_REACTIVE_POWER,
    )
    const reactiveSetpointTrace = realtimeData.data?.traces?.find(
      (t) =>
        t.sensor_type_id === SensorTypeEnum.PV_INVERTER_REACTIVE_POWER_SETPOINT,
    )

    if (
      !reactiveTrace ||
      !realtimeData.data?.device_names ||
      realtimeData.data.device_names.length === 0
    ) {
      return []
    }

    const deviceNames = realtimeData.data.device_names.filter(
      (n): n is string => n !== null,
    )
    const reactiveValues =
      reactiveTrace.values?.map((v) => (v !== null ? v : 0)) || []
    const reactiveSetpointValues =
      reactiveSetpointTrace?.values?.map((v) => (v !== null ? v : 0)) || []

    const traces: Data[] = [
      {
        x: deviceNames,
        y: reactiveValues,
        type: 'bar' as const,
        name: 'Measured Reactive Power',
        marker: { color: '#9b59b6' },
      },
    ]

    if (reactiveSetpointTrace && reactiveSetpointValues.length > 0) {
      traces.push({
        x: deviceNames,
        y: reactiveSetpointValues,
        type: 'scatter' as const,
        mode: 'markers' as const,
        name: 'Reactive Power Set Point',
        marker: {
          color: '#3498db',
          size: 12,
          opacity: 0.01,
        },
        showlegend: true,
        hoverinfo: 'x+y' as const,
        hovertemplate:
          '<b>Reactive Power Set Point</b><br>%{x}<br>%{y:.2f} MVar<extra></extra>',
      } satisfies Data)
    }

    return traces
  }, [realtimeData.data])

  const reactivePowerSetpointShapes = useMemo(() => {
    const reactiveSetpointTrace = realtimeData.data?.traces?.find(
      (t) =>
        t.sensor_type_id === SensorTypeEnum.PV_INVERTER_REACTIVE_POWER_SETPOINT,
    )

    if (
      !reactiveSetpointTrace ||
      !realtimeData.data?.device_names ||
      realtimeData.data.device_names.length === 0
    ) {
      return []
    }

    const deviceNames = realtimeData.data.device_names.filter(
      (n): n is string => n !== null,
    )
    const setpointValues =
      reactiveSetpointTrace.values?.map((v) => (v !== null ? v : 0)) || []

    const totalDevices = deviceNames.length
    return deviceNames
      .map((_deviceName, index) => {
        if (setpointValues[index] === undefined) return null

        const deviceWidth = 1 / totalDevices
        const deviceCenter = (index + 0.5) / totalDevices
        const segmentWidth = deviceWidth * 0.8

        return {
          type: 'line' as const,
          x0: deviceCenter - segmentWidth / 2,
          x1: deviceCenter + segmentWidth / 2,
          y0: setpointValues[index],
          y1: setpointValues[index],
          xref: 'paper' as const,
          yref: 'y' as const,
          line: {
            color: '#3498db',
            width: 2,
          },
        }
      })
      .filter((shape): shape is NonNullable<typeof shape> => shape !== null)
  }, [realtimeData.data])

  const yAxisRangeComputed = useMemo(() => {
    if (!maxCapacityMWac) return undefined
    const reactiveTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_REACTIVE_POWER,
    )
    const reactiveSetpointTrace = realtimeData.data?.traces?.find(
      (t) =>
        t.sensor_type_id === SensorTypeEnum.PV_INVERTER_REACTIVE_POWER_SETPOINT,
    )
    const allValues = [
      ...(reactiveTrace?.values?.filter((v): v is number => v !== null) || []),
      ...(reactiveSetpointTrace?.values?.filter(
        (v): v is number => v !== null,
      ) || []),
    ]
    const minValue = allValues.length > 0 ? Math.min(...allValues) : 0
    const maxValue = maxCapacityMWac
    return [Math.min(minValue, -maxValue), maxValue] as [number, number]
  }, [realtimeData.data, maxCapacityMWac])

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
      title="Reactive Power"
      style={{ height: '400px' }}
      allowMinimize={true}
      storageKey={`pv-pcs-realtime-reactive-power-${projectId}`}
    >
      <PlotlyPlot
        data={reactivePowerChartData}
        layout={{
          uirevision: `reactive-power-${projectId}`,
          yaxis: {
            title: { text: 'Power (MVar)' },
            range: userZoomed && yAxisRange ? yAxisRange : yAxisRangeComputed,
          },
          xaxis: {
            title: { text: 'PCS Device' },
            range:
              userZoomed && xAxisRange
                ? xAxisRange
                : reactivePowerChartData.length > 0 &&
                    reactivePowerChartData[0] &&
                    'x' in reactivePowerChartData[0] &&
                    Array.isArray(reactivePowerChartData[0].x)
                  ? [
                      -0.5,
                      (reactivePowerChartData[0].x as string[]).length - 0.5,
                    ]
                  : undefined,
          },
          shapes: reactivePowerSetpointShapes,
        }}
        onRelayout={handleRelayout}
        isLoading={realtimeData.isLoading}
        error={realtimeData.error}
        noDataMessage="No data available. Required sensor types: PV PCS Reactive Power (optional: PV PCS Reactive Power Setpoint)"
      />
    </CustomCard>
  )
}
