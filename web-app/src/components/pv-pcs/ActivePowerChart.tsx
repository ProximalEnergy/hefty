import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import {
  useGetExpectedPowerByDeviceTypeID,
  useGetRealTimeByDeviceTypeID,
} from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { AdaptiveGisMap } from '@/pages/projects/gis/adaptive-gis'
import { QUERY_TIME } from '@/utils/queryTiming'
import { SegmentedControl } from '@mantine/core'
import type { Data, PlotRelayoutEvent } from 'plotly.js'
import { useMemo, useState } from 'react'
import { useParams } from 'react-router'

const PV_INVERTER_DEVICE_TYPE_ID = DeviceTypeEnum.PV_INVERTER

interface ActivePowerChartProps {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
  maxCapacityMWac: number | null
  hasExpectedEnergyIntegration?: boolean
}

export const ActivePowerChartPvPcs = ({
  realtimeData,
  maxCapacityMWac,
  hasExpectedEnergyIntegration,
}: ActivePowerChartProps) => {
  const { projectId } = useParams<{ projectId: string }>()
  const [viewMode, setViewMode] = useState<'chart' | 'map'>('chart')

  const pcsExpectedPower = useGetExpectedPowerByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: PV_INVERTER_DEVICE_TYPE_ID,
    },
    queryOptions: {
      enabled: !!projectId && hasExpectedEnergyIntegration === true,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      staleTime: QUERY_TIME.TWENTY_FIVE_SECONDS,
    },
  })

  const [userZoomed, setUserZoomed] = useState(false)
  const [yAxisRange, setYAxisRange] = useState<[number, number] | null>(null)
  const [xAxisRange, setXAxisRange] = useState<[number, number] | null>(null)

  const activePowerChartData = useMemo(() => {
    const powerTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_AC_POWER,
    )
    const setpointTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_AC_POWER_SETPOINT,
    )

    if (
      !powerTrace ||
      !realtimeData.data?.device_names ||
      realtimeData.data.device_names.length === 0
    ) {
      return []
    }

    const deviceNames = realtimeData.data.device_names.filter(
      (n): n is string => n !== null,
    )
    const powerValues =
      powerTrace.values?.map((v) => (v !== null ? v : 0)) || []
    const setpointValues =
      setpointTrace?.values?.map((v) => (v !== null ? v : 0)) || []

    const traces: Data[] = [
      {
        x: deviceNames,
        y: powerValues,
        type: 'bar' as const,
        name: 'Measured Active Power',
        marker: { color: '#e74c3c' },
      },
    ]

    if (setpointTrace && setpointValues.length > 0) {
      traces.push({
        x: deviceNames,
        y: setpointValues,
        type: 'scatter' as const,
        mode: 'markers' as const,
        name: 'Active Power Set Point',
        marker: {
          color: '#3498db',
          size: 12,
          opacity: 0.01,
        },
        showlegend: true,
        hoverinfo: 'x+y' as const,
        hovertemplate:
          '<b>Active Power Set Point</b><br>%{x}<br>%{y:.2f} MWac<extra></extra>',
      } satisfies Data)
    }

    if (
      hasExpectedEnergyIntegration === true &&
      pcsExpectedPower.data?.expected_power
    ) {
      const expectedPowerValues: number[] = []
      if (
        realtimeData.data.device_ids &&
        realtimeData.data.device_ids.length > 0
      ) {
        realtimeData.data.device_ids.forEach((deviceId) => {
          const expectedPower = pcsExpectedPower.data.expected_power[deviceId]
          if (expectedPower !== null && expectedPower !== undefined) {
            expectedPowerValues.push(expectedPower)
          } else {
            expectedPowerValues.push(0)
          }
        })
      }

      if (expectedPowerValues.length > 0) {
        traces.push({
          x: deviceNames,
          y: expectedPowerValues,
          type: 'scatter' as const,
          mode: 'markers' as const,
          name: 'Expected Power',
          marker: {
            color: '#ff9800',
            size: 12,
            opacity: 0.01,
          },
          showlegend: true,
          hoverinfo: 'x+y' as const,
          hovertemplate:
            '<b>Expected Power</b><br>%{x}<br>%{y:.2f} MWac<extra></extra>',
        } satisfies Data)
      }
    }

    if (maxCapacityMWac !== null) {
      traces.push({
        x: [deviceNames[0], deviceNames[deviceNames.length - 1]],
        y: [maxCapacityMWac, maxCapacityMWac],
        type: 'scatter' as const,
        mode: 'lines' as const,
        name: 'Max Capacity',
        line: {
          color: '#95a5a6',
          dash: 'dash' as const,
          width: 2,
        },
        showlegend: true,
        hoverinfo: 'skip' as const,
      } satisfies Data)
    }

    return traces
  }, [
    realtimeData.data,
    maxCapacityMWac,
    pcsExpectedPower.data,
    hasExpectedEnergyIntegration,
  ])

  const setpointShapes = useMemo(() => {
    const setpointTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_AC_POWER_SETPOINT,
    )

    if (
      !setpointTrace ||
      !realtimeData.data?.device_names ||
      realtimeData.data.device_names.length === 0
    ) {
      return []
    }

    const deviceNames = realtimeData.data.device_names.filter(
      (n): n is string => n !== null,
    )
    const setpointValues =
      setpointTrace.values?.map((v) => (v !== null ? v : 0)) || []

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

  const expectedPowerShapes = useMemo(() => {
    if (
      hasExpectedEnergyIntegration === false ||
      !pcsExpectedPower.data?.expected_power ||
      !realtimeData.data?.device_names ||
      realtimeData.data.device_names.length === 0 ||
      !realtimeData.data.device_ids
    ) {
      return []
    }

    const deviceNames = realtimeData.data.device_names.filter(
      (n): n is string => n !== null,
    )

    const expectedPowerValues: (number | null)[] = []
    realtimeData.data.device_ids.forEach((deviceId) => {
      const expectedPower = pcsExpectedPower.data.expected_power[deviceId]
      expectedPowerValues.push(expectedPower ?? null)
    })

    const totalDevices = deviceNames.length
    return deviceNames
      .map((_deviceName, index) => {
        const expectedPower = expectedPowerValues[index]
        if (expectedPower === null || expectedPower === undefined) return null

        const deviceWidth = 1 / totalDevices
        const deviceCenter = (index + 0.5) / totalDevices
        const segmentWidth = deviceWidth * 0.8

        return {
          type: 'line' as const,
          x0: deviceCenter - segmentWidth / 2,
          x1: deviceCenter + segmentWidth / 2,
          y0: expectedPower,
          y1: expectedPower,
          xref: 'paper' as const,
          yref: 'y' as const,
          line: {
            color: '#ff9800',
            width: 2,
          },
        }
      })
      .filter((shape): shape is NonNullable<typeof shape> => shape !== null)
  }, [realtimeData.data, pcsExpectedPower.data, hasExpectedEnergyIntegration])

  const yAxisRangeComputed = useMemo(() => {
    if (!maxCapacityMWac) return undefined
    const powerTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_AC_POWER,
    )
    const setpointTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.PV_INVERTER_AC_POWER_SETPOINT,
    )

    const expectedPowerValues: number[] = []
    if (
      pcsExpectedPower.data?.expected_power &&
      realtimeData.data?.device_ids
    ) {
      realtimeData.data.device_ids.forEach((deviceId) => {
        const expectedPower = pcsExpectedPower.data.expected_power[deviceId]
        if (expectedPower !== null && expectedPower !== undefined) {
          expectedPowerValues.push(expectedPower)
        }
      })
    }

    const allValues = [
      ...(powerTrace?.values?.filter((v): v is number => v !== null) || []),
      ...(setpointTrace?.values?.filter((v): v is number => v !== null) || []),
      ...expectedPowerValues,
    ]
    const minValue = allValues.length > 0 ? Math.min(0, ...allValues) : 0
    return [minValue, maxCapacityMWac] as [number, number]
  }, [realtimeData.data, maxCapacityMWac, pcsExpectedPower.data])

  const handlePvActivePowerRelayout = (event: Readonly<PlotRelayoutEvent>) => {
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
      title="Active Power"
      style={{ height: '400px' }}
      allowMinimize={true}
      storageKey={`pv-pcs-realtime-active-power-${projectId}`}
      fill={true}
      bodyStyle={{ position: 'relative', height: '100%' }}
      headerChildren={
        <SegmentedControl
          value={viewMode}
          onChange={(value) => setViewMode(value as 'chart' | 'map')}
          data={[
            { label: 'Chart', value: 'chart' },
            { label: 'Map', value: 'map' },
          ]}
          size="xs"
          onClick={(e) => e.stopPropagation()}
        />
      }
    >
      <div style={{ position: 'relative', height: '100%', width: '100%' }}>
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            visibility: viewMode === 'chart' ? 'visible' : 'hidden',
            pointerEvents: viewMode === 'chart' ? 'auto' : 'none',
            zIndex: viewMode === 'chart' ? 1 : 0,
          }}
        >
          <PlotlyPlot
            data={activePowerChartData}
            layout={{
              uirevision: `active-power-${projectId}`,
              yaxis: {
                title: { text: 'Power (MWac)' },
                range:
                  userZoomed && yAxisRange ? yAxisRange : yAxisRangeComputed,
              },
              xaxis: {
                title: { text: 'PCS Device' },
                range:
                  userZoomed && xAxisRange
                    ? xAxisRange
                    : activePowerChartData.length > 0 &&
                        activePowerChartData[0] &&
                        'x' in activePowerChartData[0] &&
                        Array.isArray(activePowerChartData[0].x)
                      ? [
                          -0.5,
                          (activePowerChartData[0].x as string[]).length - 0.5,
                        ]
                      : undefined,
              },
              shapes: [...setpointShapes, ...expectedPowerShapes],
            }}
            onRelayout={handlePvActivePowerRelayout}
            isLoading={realtimeData.isLoading || pcsExpectedPower.isLoading}
            error={realtimeData.error || pcsExpectedPower.error}
            noDataMessage="No data available. Required sensor types: PV Inverter AC Power (optional: PV Inverter AC Power Setpoint)"
          />
        </div>
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            visibility: viewMode === 'map' ? 'visible' : 'hidden',
            pointerEvents: viewMode === 'map' ? 'auto' : 'none',
            zIndex: viewMode === 'map' ? 1 : 0,
          }}
        >
          <AdaptiveGisMap />
        </div>
      </div>
    </CustomCard>
  )
}
