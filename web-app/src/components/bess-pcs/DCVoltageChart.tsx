import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import { useBessPcsFaultData } from '@/components/bess-pcs/useBessPcsFaultData'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { SegmentedControl } from '@mantine/core'
import type { Data, PlotRelayoutEvent } from 'plotly.js'
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router'

type ViewSource = 'pcs' | 'module_group' | 'module'

const PCS_DC_SENSOR = SensorTypeEnum.BESS_PCS_DC_VOLTAGE
const MODULE_DC_SENSOR = SensorTypeEnum.BESS_PCS_MODULE_DC_VOLTAGE
const MODULE_GROUP_DC_SENSOR = SensorTypeEnum.BESS_PCS_MODULE_GROUP_DC_VOLTAGE

interface DCVoltageChartProps {
  realtimeData: ReturnType<typeof useGetRealTimeByDeviceTypeID>
}

export const DCVoltageChart = ({ realtimeData }: DCVoltageChartProps) => {
  const { projectId } = useParams<{
    projectId: string
  }>()
  const [viewSource, setViewSource] = useState<ViewSource>('module_group')

  const moduleData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_PCS_MODULE,
    },
    queryParams: {
      sensor_type_ids: [MODULE_DC_SENSOR],
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
      sensor_type_ids: [MODULE_GROUP_DC_SENSOR],
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

  const [userZoomed, setUserZoomed] = useState(false)
  const [yAxisRange, setYAxisRange] = useState<[number, number] | null>(null)
  const [xAxisRange, setXAxisRange] = useState<[number, number] | null>(null)

  useEffect(() => {
    setUserZoomed(false)
    setYAxisRange(null)
    setXAxisRange(null)
  }, [viewSource])

  const dcVoltageData = useMemo(() => {
    const hasNonNull = (vals?: (number | null)[]) =>
      vals?.some((v) => v !== null && v !== undefined)
    const findTrace = (data: typeof realtimeData.data, sensorId: number) =>
      data?.traces?.find(
        (t) => t.sensor_type_id === sensorId && hasNonNull(t.values),
      )

    const sources: Record<
      ViewSource,
      { data: typeof realtimeData.data; sensorId: number; xLabel: string }
    > = {
      pcs: {
        data: realtimeData.data,
        sensorId: PCS_DC_SENSOR,
        xLabel: 'PCS Device',
      },
      module_group: {
        data: groupData.data,
        sensorId: MODULE_GROUP_DC_SENSOR,
        xLabel: 'PCS Module Group',
      },
      module: {
        data: moduleData.data,
        sensorId: MODULE_DC_SENSOR,
        xLabel: 'PCS Module',
      },
    }

    const { data, sensorId, xLabel } = sources[viewSource]
    const trace = findTrace(data, sensorId)

    if (trace && data?.device_names && data.device_names.length > 0) {
      const names = data.device_names.filter((n): n is string => n !== null)
      const faultInfo =
        viewSource === 'pcs'
          ? faultData.pcs
          : viewSource === 'module'
            ? faultData.module
            : faultData.moduleGroup
      const hoverTexts = names.map(
        (name) =>
          faultInfo?.hoverMap.get(name) ??
          '<b>Faults/Errors/Warnings</b><br>None',
      )
      const faultDeviceNames = names.filter((name) =>
        faultInfo?.faultSet.has(name),
      )
      const yVals = trace.values?.filter((v): v is number => v !== null) || []
      const yBottom = yVals.length > 0 ? Math.min(...yVals) - 20 : -20

      const traces: Data[] = [
        {
          x: names,
          y: trace.values?.map((v) => (v !== null ? v : 0)) || [],
          type: 'bar' as const,
          name: 'DC Voltage',
          customdata: hoverTexts,
          hovertemplate:
            '<b>%{x}</b><br>DC Voltage: %{y:.1f} V<br><br>%{customdata}<extra></extra>',
          marker: { color: '#f39c12' },
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

      return { data: traces, xLabel }
    }

    return { data: [], xLabel }
  }, [realtimeData, moduleData, groupData, viewSource, faultData])

  const faultInfo =
    viewSource === 'pcs'
      ? faultData.pcs
      : viewSource === 'module'
        ? faultData.module
        : faultData.moduleGroup

  const yAxisRangeComputed = useMemo(() => {
    if (dcVoltageData.data.length === 0) {
      return undefined
    }
    const firstTrace = dcVoltageData.data[0]
    const values =
      firstTrace && 'y' in firstTrace
        ? (firstTrace.y as number[] | undefined)
        : undefined
    if (!values || values.length === 0) {
      return [0, 100] as [number, number]
    }
    const maxVal = Math.max(
      ...values.filter((v) => v !== null && v !== undefined),
    )
    const minVal = Math.min(
      0,
      ...values.filter((v) => v !== null && v !== undefined),
    )
    const hasFaults = (faultInfo?.faultSet.size ?? 0) > 0
    const bottom = hasFaults
      ? Math.min(0, minVal * 1.1) - 25
      : Math.min(0, minVal * 1.1)
    return [bottom, Math.max(100, maxVal * 1.1)] as [number, number]
  }, [dcVoltageData.data, faultInfo?.faultSet.size])

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

  const titleLabel =
    viewSource === 'pcs'
      ? 'PCS Device'
      : viewSource === 'module_group'
        ? 'PCS Module Group'
        : 'PCS Module'

  return (
    <CustomCard
      title={`DC Voltage (${titleLabel})`}
      style={{ height: '400px' }}
      allowMinimize={true}
      storageKey={`bess-pcs-realtime-dc-voltage-${projectId}`}
      headerChildren={
        <SegmentedControl
          value={viewSource}
          onChange={(v) => setViewSource(v as ViewSource)}
          data={[
            { label: 'PCS', value: 'pcs' },
            { label: 'PCS Module Group', value: 'module_group' },
            { label: 'PCS Module', value: 'module' },
          ]}
          size="xs"
          onClick={(e) => e.stopPropagation()}
        />
      }
    >
      <PlotlyPlot
        data={dcVoltageData.data}
        layout={{
          uirevision: `bess-dc-voltage-${projectId}-${viewSource}`,
          yaxis: {
            title: { text: 'Voltage (V)' },
            range: userZoomed && yAxisRange ? yAxisRange : yAxisRangeComputed,
          },
          xaxis: {
            title: {
              text: dcVoltageData.xLabel,
            },
            range: userZoomed && xAxisRange ? xAxisRange : undefined,
          },
        }}
        onRelayout={handleRelayout}
        isLoading={
          realtimeData.isLoading || moduleData.isLoading || groupData.isLoading
        }
        error={realtimeData.error || moduleData.error || groupData.error}
        noDataMessage="No DC voltage data available."
      />
    </CustomCard>
  )
}
