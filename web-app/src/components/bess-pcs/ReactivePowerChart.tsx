import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import { useBessPcsFaultData } from '@/components/bess-pcs/useBessPcsFaultData'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import type { Data, PlotRelayoutEvent } from 'plotly.js'
import { useMemo, useState } from 'react'
import { useParams } from 'react-router'

const REACTIVE_SENSORS: number[] = [
  SensorTypeEnum.BESS_PCS_REACTIVE_POWER,
  SensorTypeEnum.BESS_PCS_MODULE_REACTIVE_POWER,
  SensorTypeEnum.BESS_PCS_MODULE_GROUP_REACTIVE_POWER,
]

interface ReactivePowerChartProps {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
  maxCapacityMWac: number | null
}

export const ReactivePowerChart = ({
  realtimeData,
  maxCapacityMWac,
}: ReactivePowerChartProps) => {
  const { projectId } = useParams<{
    projectId: string
  }>()
  const [userZoomed, setUserZoomed] = useState(false)
  const [yAxisRange, setYAxisRange] = useState<[number, number] | null>(null)
  const [xAxisRange, setXAxisRange] = useState<[number, number] | null>(null)

  const moduleData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_PCS_MODULE,
    },
    queryParams: {
      sensor_type_ids: REACTIVE_SENSORS,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000,
      staleTime: 15000,
    },
  })

  const groupData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
    },
    queryParams: {
      sensor_type_ids: REACTIVE_SENSORS,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: 30000,
      staleTime: 15000,
    },
  })

  const faultData = useBessPcsFaultData({
    pcs: { data: realtimeData.data },
    module: { data: moduleData.data },
    moduleGroup: { data: groupData.data },
  })

  const resolved = useMemo(() => {
    const hasNonNull = (vals?: (number | null)[]) =>
      vals?.some((v) => v !== null && v !== undefined)
    const find = (data: typeof realtimeData.data) =>
      data?.traces?.find(
        (t) =>
          REACTIVE_SENSORS.includes(t.sensor_type_id) && hasNonNull(t.values),
      )

    const pcsTrace = find(realtimeData.data)
    if (pcsTrace && realtimeData.data?.device_names?.length) {
      return {
        trace: pcsTrace,
        names: realtimeData.data.device_names.filter(
          (n): n is string => n !== null,
        ),
        xLabel: 'PCS Device',
      }
    }

    const modTrace = find(moduleData.data)
    if (modTrace && moduleData.data?.device_names?.length) {
      return {
        trace: modTrace,
        names: moduleData.data.device_names.filter(
          (n): n is string => n !== null,
        ),
        xLabel: 'PCS Module',
      }
    }

    const grpTrace = find(groupData.data)
    if (grpTrace && groupData.data?.device_names?.length) {
      return {
        trace: grpTrace,
        names: groupData.data.device_names.filter(
          (n): n is string => n !== null,
        ),
        xLabel: 'PCS Module Group',
      }
    }

    return null
  }, [realtimeData, moduleData, groupData])

  const faultInfo = useMemo(() => {
    if (!resolved) return null
    const key =
      resolved.xLabel === 'PCS Device'
        ? 'pcs'
        : resolved.xLabel === 'PCS Module'
          ? 'module'
          : 'moduleGroup'
    return faultData[key]
  }, [resolved, faultData])

  const chartData = useMemo((): Data[] => {
    if (!resolved) return []
    const values = resolved.trace.values?.map((v) => (v !== null ? v : 0)) || []

    const capacitiveTrace = realtimeData.data?.traces?.find(
      (t) =>
        t.sensor_type_id ===
        SensorTypeEnum.BESS_PCS_AVAILABLE_CAPACITIVE_REACTIVE_POWER,
    )
    const inductiveTrace = realtimeData.data?.traces?.find(
      (t) =>
        t.sensor_type_id ===
        SensorTypeEnum.BESS_PCS_AVAILABLE_INDUCTIVE_REACTIVE_POWER,
    )

    const capacitiveValues =
      capacitiveTrace?.values?.map((v) => (v !== null ? -Math.abs(v) : null)) ||
      []
    const inductiveValues =
      inductiveTrace?.values?.map((v) => (v !== null ? Math.abs(v) : null)) ||
      []

    const deviceNames =
      realtimeData.data?.device_names?.filter((n): n is string => n !== null) ||
      []

    const hoverTexts = resolved.names.map(
      (name) =>
        faultInfo?.hoverMap.get(name) ??
        '<b>Faults/Errors/Warnings</b><br>None',
    )

    const faultDeviceNames = resolved.names.filter((name) =>
      faultInfo?.faultSet.has(name),
    )
    const yBottom = maxCapacityMWac !== null ? -maxCapacityMWac - 0.3 : -1

    const traces: Data[] = [
      {
        x: resolved.names,
        y: values,
        type: 'bar' as const,
        name: 'Reactive Power',
        customdata: hoverTexts,
        hovertemplate:
          '<b>%{x}</b><br>Reactive Power: %{y:.2f} MVar<br><br>%{customdata}<extra></extra>',
        marker: { color: '#9b59b6' },
      },
    ]

    if (faultDeviceNames.length > 0) {
      traces.push({
        x: faultDeviceNames,
        y: faultDeviceNames.map(() => yBottom),
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

    if (capacitiveValues.some((v) => v !== null)) {
      traces.push({
        x: deviceNames,
        y: capacitiveValues,
        type: 'scatter' as const,
        mode: 'markers' as const,
        name: 'Available Capacitive',
        marker: {
          color: '#9b59b6',
          symbol: 'triangle-down',
          size: 8,
        },
      } satisfies Data)
    }

    if (inductiveValues.some((v) => v !== null)) {
      traces.push({
        x: deviceNames,
        y: inductiveValues,
        type: 'scatter' as const,
        mode: 'markers' as const,
        name: 'Available Inductive',
        marker: {
          color: '#9b59b6',
          symbol: 'triangle-up',
          size: 8,
        },
      } satisfies Data)
    }

    return traces
  }, [resolved, realtimeData.data, faultInfo, maxCapacityMWac])

  const yAxisRangeComputed = useMemo(() => {
    if (!maxCapacityMWac || !resolved) {
      return undefined
    }
    const allValues =
      resolved.trace.values?.filter((v): v is number => v !== null) || []
    const minVal = allValues.length > 0 ? Math.min(...allValues) : 0
    const hasFaults = (faultInfo?.faultSet.size ?? 0) > 0
    const bottom = hasFaults
      ? Math.min(minVal, -maxCapacityMWac) - 0.5
      : Math.min(minVal, -maxCapacityMWac)
    return [bottom, maxCapacityMWac] as [number, number]
  }, [resolved, maxCapacityMWac, faultInfo?.faultSet.size])

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
      title="Reactive Power"
      style={{ height: '400px' }}
      allowMinimize={true}
      storageKey={`bess-pcs-realtime-reactive-power-${projectId}`}
    >
      <PlotlyPlot
        data={chartData}
        layout={{
          uirevision: `bess-reactive-power-${projectId}`,
          yaxis: {
            title: { text: 'Power (MVar)' },
            range: resolvedYAxisRange,
          },
          xaxis: {
            title: {
              text: resolved?.xLabel || 'PCS Device',
            },
            range: resolvedXAxisRange,
          },
        }}
        onRelayout={handleRelayout}
        isLoading={
          realtimeData.isLoading || moduleData.isLoading || groupData.isLoading
        }
        error={realtimeData.error || moduleData.error || groupData.error}
        noDataMessage="No reactive power data available."
      />
    </CustomCard>
  )
}
