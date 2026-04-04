import { SensorTypeEnum } from '@/api/enumerations'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import { useBessPcsFaultData } from '@/components/bess-pcs/useBessPcsFaultData'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import AdaptiveGisBESS from '@/pages/projects/gis/adaptive-gis-bess'
import { SegmentedControl } from '@mantine/core'
import type { Data, PlotRelayoutEvent } from 'plotly.js'
import { useMemo, useState } from 'react'
import { useParams } from 'react-router'

interface ActivePowerChartProps {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
  maxCapacityMWac: number | null
}

export const ActivePowerChart = ({
  realtimeData,
  maxCapacityMWac,
}: ActivePowerChartProps) => {
  const { projectId } = useParams<{
    projectId: string
  }>()
  const [viewMode, setViewMode] = useState<'chart' | 'map'>('chart')
  const [userZoomed, setUserZoomed] = useState(false)
  const [yAxisRange, setYAxisRange] = useState<[number, number] | null>(null)
  const [xAxisRange, setXAxisRange] = useState<[number, number] | null>(null)

  const { pcs } = useBessPcsFaultData({
    pcs: { data: realtimeData.data },
  })
  const { faultSet: pcsWithFaults, hoverMap: hoverByPcsDeviceName } = pcs

  const chartData = useMemo(() => {
    const powerTrace = realtimeData.data?.traces?.find(
      (t) => t.sensor_type_id === SensorTypeEnum.BESS_PCS_AC_POWER,
    )

    if (
      !powerTrace ||
      !realtimeData.data?.device_names ||
      realtimeData.data.device_names.length === 0
    ) {
      return []
    }

    const rawDeviceNames = realtimeData.data.device_names
    const rawPowerValues = powerTrace.values || []
    const pointCount = Math.min(rawDeviceNames.length, rawPowerValues.length)

    const deviceNames = Array.from(
      { length: pointCount },
      (_, idx) => rawDeviceNames[idx] ?? `Device ${idx + 1}`,
    )
    const powerValues = rawPowerValues
      .slice(0, pointCount)
      .map((v) => (v !== null ? v : 0))
    const hoverTexts = deviceNames.map(
      (name) =>
        hoverByPcsDeviceName.get(name) ??
        '<b>Module Group Faults/Errors/Warnings</b><br>None<br><br><b>Module Faults/Errors/Warnings</b><br>None',
    )

    const chargeTrace = realtimeData.data?.traces?.find(
      (t) =>
        t.sensor_type_id === SensorTypeEnum.BESS_PCS_AVAILABLE_CHARGE_POWER,
    )
    const dischargeTrace = realtimeData.data?.traces?.find(
      (t) =>
        t.sensor_type_id === SensorTypeEnum.BESS_PCS_AVAILABLE_DISCHARGE_POWER,
    )

    const chargeValues =
      chargeTrace?.values
        ?.slice(0, pointCount)
        .map((v) => (v !== null ? -Math.abs(v) : null)) || []
    const dischargeValues =
      dischargeTrace?.values
        ?.slice(0, pointCount)
        .map((v) => (v !== null ? Math.abs(v) : null)) || []

    const faultDeviceNames = deviceNames.filter((name) =>
      pcsWithFaults.has(name),
    )
    const faultY = maxCapacityMWac !== null ? -maxCapacityMWac - 0.3 : -1

    const traces: Data[] = [
      {
        x: deviceNames,
        y: powerValues,
        type: 'bar' as const,
        name: 'Active Power',
        customdata: hoverTexts,
        hovertemplate:
          '<b>%{x}</b><br>Active Power: %{y:.2f} MWac<br><br>%{customdata}<extra></extra>',
        marker: {
          color: '#2ecc71',
        },
      },
    ]

    if (faultDeviceNames.length > 0) {
      traces.push({
        x: faultDeviceNames,
        y: faultDeviceNames.map(() => faultY),
        type: 'scatter' as const,
        mode: 'markers' as const,
        name: 'Fault/Warning',
        marker: {
          symbol: 'circle',
          size: 10,
          color: '#e74c3c',
          line: { width: 0 },
        },
        hovertemplate: '<b>%{x}</b><br>Faults/Errors/Warnings<extra></extra>',
      } satisfies Data)
    }

    if (chargeValues.some((v) => v !== null)) {
      traces.push({
        x: deviceNames,
        y: chargeValues,
        type: 'scatter' as const,
        mode: 'markers' as const,
        name: 'Available Charge',
        marker: {
          color: '#2ecc71',
          symbol: 'triangle-down',
          size: 8,
        },
        hoverinfo: 'skip' as const,
      } satisfies Data)
    }

    if (dischargeValues.some((v) => v !== null)) {
      traces.push({
        x: deviceNames,
        y: dischargeValues,
        type: 'scatter' as const,
        mode: 'markers' as const,
        name: 'Available Discharge',
        marker: {
          color: '#2ecc71',
          symbol: 'triangle-up',
          size: 8,
        },
        hoverinfo: 'skip' as const,
      } satisfies Data)
    }

    if (maxCapacityMWac !== null) {
      const xRange = [deviceNames[0], deviceNames[deviceNames.length - 1]]
      traces.push({
        x: xRange,
        y: [maxCapacityMWac, maxCapacityMWac],
        type: 'scatter' as const,
        mode: 'lines' as const,
        name: 'Max Discharge',
        line: {
          color: '#95a5a6',
          dash: 'dash' as const,
          width: 2,
        },
        showlegend: true,
        hoverinfo: 'skip' as const,
      } satisfies Data)
      traces.push({
        x: xRange,
        y: [-maxCapacityMWac, -maxCapacityMWac],
        type: 'scatter' as const,
        mode: 'lines' as const,
        name: 'Max Charge',
        line: {
          color: '#95a5a6',
          dash: 'dot' as const,
          width: 2,
        },
        showlegend: true,
        hoverinfo: 'skip' as const,
      } satisfies Data)
    }

    return traces
  }, [realtimeData.data, maxCapacityMWac, hoverByPcsDeviceName, pcsWithFaults])

  const yAxisRangeComputed = useMemo(() => {
    if (!maxCapacityMWac) return undefined
    const hasFaults = pcsWithFaults.size > 0
    const bottom = hasFaults ? -maxCapacityMWac - 0.5 : -maxCapacityMWac
    return [bottom, maxCapacityMWac] as [number, number]
  }, [maxCapacityMWac, pcsWithFaults.size])

  const xAxisRangeComputed = useMemo(() => {
    if (
      chartData.length === 0 ||
      !chartData[0] ||
      !('x' in chartData[0]) ||
      !Array.isArray(chartData[0].x)
    ) {
      return undefined
    }

    return [-0.5, (chartData[0].x as string[]).length - 0.5] as [number, number]
  }, [chartData])

  const resolvedYAxisRange =
    userZoomed && yAxisRange ? yAxisRange : yAxisRangeComputed
  const resolvedXAxisRange =
    userZoomed && xAxisRange ? xAxisRange : xAxisRangeComputed

  const handleRelayout = (event: Readonly<PlotRelayoutEvent>) => {
    let zoomed = false

    if (
      event['yaxis.range[0]'] !== undefined &&
      event['yaxis.range[1]'] !== undefined
    ) {
      setYAxisRange([
        event['yaxis.range[0]'] as number,
        event['yaxis.range[1]'] as number,
      ])
      zoomed = true
    } else if (event['yaxis.autorange'] === true) {
      setYAxisRange(null)
    }

    if (
      event['xaxis.range[0]'] !== undefined &&
      event['xaxis.range[1]'] !== undefined
    ) {
      setXAxisRange([
        event['xaxis.range[0]'] as number,
        event['xaxis.range[1]'] as number,
      ])
      zoomed = true
    } else if (event['xaxis.autorange'] === true) {
      setXAxisRange(null)
    }

    if (
      event['yaxis.autorange'] === true &&
      event['xaxis.autorange'] === true
    ) {
      setUserZoomed(false)
    } else if (zoomed) {
      setUserZoomed(true)
    }
  }

  return (
    <CustomCard
      title="Active Power"
      info="Positive values indicate discharging, negative values indicate charging."
      style={{ height: '400px' }}
      allowMinimize={true}
      storageKey={`bess-pcs-realtime-active-power-${projectId}`}
      fill={true}
      bodyStyle={{
        position: 'relative',
        height: '100%',
      }}
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
      <div
        style={{
          position: 'relative',
          height: '100%',
          width: '100%',
        }}
      >
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
            data={chartData}
            layout={{
              uirevision: `bess-active-power-${projectId}`,
              yaxis: {
                title: { text: 'Power (MWac)' },
                zeroline: true,
                zerolinecolor: '#888',
                zerolinewidth: 1,
                range: resolvedYAxisRange,
              },
              xaxis: {
                title: { text: 'PCS Device' },
                range: resolvedXAxisRange,
              },
            }}
            onRelayout={handleRelayout}
            isLoading={realtimeData.isLoading}
            error={realtimeData.error}
            noDataMessage="No data available. Required sensor type: BESS PCS AC Power"
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
          <AdaptiveGisBESS />
        </div>
      </div>
    </CustomCard>
  )
}
