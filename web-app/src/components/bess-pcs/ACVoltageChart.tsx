import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import { useBessPcsFaultData } from '@/components/bess-pcs/useBessPcsFaultData'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { QUERY_TIME } from '@/utils/queryTiming'
import { SegmentedControl } from '@mantine/core'
import type { Data } from 'plotly.js'
import { useMemo, useState } from 'react'
import { useParams } from 'react-router'

type ViewSource = 'module' | 'module_group'

const MODULE_VOLTAGE_SENSORS: number[] = [
  SensorTypeEnum.BESS_PCS_MODULE_VOLTAGE_LL_AB,
  SensorTypeEnum.BESS_PCS_MODULE_VOLTAGE_LL_BC,
  SensorTypeEnum.BESS_PCS_MODULE_VOLTAGE_LL_CA,
]
const MODULE_GROUP_VOLTAGE_SENSORS: number[] = [
  SensorTypeEnum.BESS_PCS_MODULE_GROUP_VOLTAGE_LL_AB,
  SensorTypeEnum.BESS_PCS_MODULE_GROUP_VOLTAGE_LL_BC,
  SensorTypeEnum.BESS_PCS_MODULE_GROUP_VOLTAGE_LL_CA,
]

export const ACVoltageChart = () => {
  const { projectId } = useParams<{
    projectId: string
  }>()
  const [viewSource, setViewSource] = useState<ViewSource>('module')

  const moduleData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_PCS_MODULE,
    },
    queryParams: {
      sensor_type_ids: MODULE_VOLTAGE_SENSORS,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  const groupData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
    },
    queryParams: {
      sensor_type_ids: MODULE_GROUP_VOLTAGE_SENSORS,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.THIRTY_SECONDS,
      staleTime: QUERY_TIME.FIFTEEN_SECONDS,
    },
  })

  const faultData = useBessPcsFaultData({
    module: { data: moduleData.data },
    moduleGroup: { data: groupData.data },
  })

  const faultInfo =
    viewSource === 'module' ? faultData.module : faultData.moduleGroup

  const { voltageData, xLabel } = useMemo(() => {
    const hasNonNull = (vals?: (number | null)[]) =>
      vals?.some((v) => v !== null && v !== undefined)
    const buildTraces = (
      data: typeof moduleData.data,
      sensors: [number, number, number],
    ) => {
      if (!data?.device_names || data.device_names.length === 0) {
        return null
      }
      const names = data.device_names.filter((n): n is string => n !== null)
      const [sAb, sBc, sCa] = sensors
      const ab = data.traces?.find(
        (t) => t.sensor_type_id === sAb && hasNonNull(t.values),
      )
      if (!ab) return null

      const bc = data.traces?.find((t) => t.sensor_type_id === sBc)
      const ca = data.traces?.find((t) => t.sensor_type_id === sCa)

      const hoverTexts = names.map(
        (name) =>
          faultInfo?.hoverMap.get(name) ??
          '<b>Faults/Errors/Warnings</b><br>None',
      )

      const traces: Data[] = [
        {
          x: names,
          y: ab.values || [],
          type: 'bar' as const,
          name: 'AB',
          customdata: hoverTexts,
          hovertemplate:
            '<b>%{x}</b><br>AB: %{y:.1f} V<br><br>%{customdata}<extra></extra>',
          marker: { color: '#e74c3c' },
        },
        ...(bc
          ? [
              {
                x: names,
                y: bc.values || [],
                type: 'bar' as const,
                name: 'BC',
                customdata: hoverTexts,
                hovertemplate:
                  '<b>%{x}</b><br>BC: %{y:.1f} V<br><br>%{customdata}<extra></extra>',
                marker: { color: '#3498db' },
              },
            ]
          : []),
        ...(ca
          ? [
              {
                x: names,
                y: ca.values || [],
                type: 'bar' as const,
                name: 'CA',
                customdata: hoverTexts,
                hovertemplate:
                  '<b>%{x}</b><br>CA: %{y:.1f} V<br><br>%{customdata}<extra></extra>',
                marker: { color: '#2ecc71' },
              },
            ]
          : []),
      ]

      const faultDeviceNames = names.filter((name) =>
        faultInfo?.faultSet.has(name),
      )
      const yVals = [
        ...(ab.values || []),
        ...(bc?.values || []),
        ...(ca?.values || []),
      ].filter((v): v is number => v !== null)
      const yBottom = yVals.length > 0 ? Math.min(...yVals) - 10 : -10

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

      return traces
    }

    const data = viewSource === 'module' ? moduleData.data : groupData.data
    const sensors = (
      viewSource === 'module'
        ? MODULE_VOLTAGE_SENSORS
        : MODULE_GROUP_VOLTAGE_SENSORS
    ) as [number, number, number]
    const traces = buildTraces(data, sensors)
    const xLabel = viewSource === 'module' ? 'PCS Module' : 'PCS Module Group'

    return {
      voltageData: traces ?? [],
      xLabel: traces ? xLabel : '',
    }
  }, [moduleData, groupData, viewSource, faultInfo])

  const yAxisRange = useMemo(() => {
    if (voltageData.length === 0) return undefined
    const allY = voltageData.flatMap((t) =>
      'y' in t && Array.isArray(t.y)
        ? (t.y as number[]).filter((v) => v !== null && v !== undefined)
        : [],
    )
    if (allY.length === 0) return undefined
    const hasFaults = (faultInfo?.faultSet.size ?? 0) > 0
    const min = Math.min(...allY)
    const max = Math.max(...allY)
    const padding = (max - min) * 0.1 || 10
    const bottom = hasFaults ? min - padding - 15 : min - padding
    return [bottom, max + padding] as [number, number]
  }, [voltageData, faultInfo?.faultSet.size])

  return (
    <CustomCard
      title={xLabel ? `AC Voltage (${xLabel})` : 'AC Voltage'}
      style={{ height: '400px' }}
      allowMinimize={true}
      storageKey={`bess-pcs-realtime-ac-voltage-${projectId}`}
      headerChildren={
        <SegmentedControl
          value={viewSource}
          onChange={(v) => setViewSource(v as ViewSource)}
          data={[
            { label: 'PCS Module', value: 'module' },
            { label: 'PCS Module Group', value: 'module_group' },
          ]}
          size="xs"
          onClick={(e) => e.stopPropagation()}
        />
      }
    >
      <PlotlyPlot
        data={voltageData}
        layout={{
          uirevision: `bess-ac-voltage-${projectId}-${viewSource}`,
          barmode: 'group',
          yaxis: {
            title: { text: 'Voltage (V)' },
            range: yAxisRange,
          },
          xaxis: {
            title: { text: xLabel },
          },
        }}
        isLoading={moduleData.isLoading || groupData.isLoading}
        error={moduleData.error || groupData.error}
        noDataMessage="No AC voltage data available."
      />
    </CustomCard>
  )
}
