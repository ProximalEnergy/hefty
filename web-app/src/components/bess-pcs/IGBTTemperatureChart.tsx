import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetRealTimeByDeviceTypeID } from '@/api/v1/protected/web-application/projects/real_time'
import CustomCard from '@/components/CustomCard'
import { useBessPcsFaultData } from '@/components/bess-pcs/useBessPcsFaultData'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { QUERY_TIME } from '@/utils/queryTiming'
import { Group, SegmentedControl } from '@mantine/core'
import type { Data } from 'plotly.js'
import { useMemo, useState } from 'react'
import { useParams } from 'react-router'

type ViewSource = 'module' | 'module_group'

const MODULE_IGBT = SensorTypeEnum.BESS_PCS_MODULE_IGBT_TEMPERATURE
const MODULE_GROUP_IGBT = SensorTypeEnum.BESS_PCS_MODULE_GROUP_IGBT_TEMPERATURE
const MODULE_POWER_SENSORS: number[] = [
  SensorTypeEnum.BESS_PCS_MODULE_APPARENT_POWER,
  SensorTypeEnum.BESS_PCS_MODULE_AC_POWER,
]
const MODULE_GROUP_POWER_SENSORS: number[] = [
  SensorTypeEnum.BESS_PCS_MODULE_GROUP_APPARENT_POWER,
  SensorTypeEnum.BESS_PCS_MODULE_GROUP_AC_POWER,
]

interface IGBTTemperatureChartProps {
  maxCapacityMWac?: number | null
}

export const IGBTTemperatureChart = ({
  maxCapacityMWac,
}: IGBTTemperatureChartProps) => {
  const { projectId } = useParams<{
    projectId: string
  }>()
  const [viewSource, setViewSource] = useState<ViewSource>('module')
  const [viewMode, setViewMode] = useState<'bar' | 'scatter'>('bar')

  const moduleData = useGetRealTimeByDeviceTypeID({
    pathParams: {
      projectId: projectId || '-1',
      deviceTypeId: DeviceTypeEnum.BESS_PCS_MODULE,
    },
    queryParams: {
      sensor_type_ids: [MODULE_IGBT, ...MODULE_POWER_SENSORS],
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
      sensor_type_ids: [MODULE_GROUP_IGBT, ...MODULE_GROUP_POWER_SENSORS],
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

  const activeData = useMemo(() => {
    const hasNonNull = (vals?: (number | null)[]) =>
      vals?.some((v) => v !== null && v !== undefined)
    const buildResult = (data: typeof moduleData.data, source: ViewSource) => {
      const igbtSensor = source === 'module' ? MODULE_IGBT : MODULE_GROUP_IGBT
      const powerSensors =
        source === 'module' ? MODULE_POWER_SENSORS : MODULE_GROUP_POWER_SENSORS
      const igbt = data?.traces?.find(
        (t) => t.sensor_type_id === igbtSensor && hasNonNull(t.values),
      )
      const power = data?.traces?.find((t) =>
        powerSensors.includes(t.sensor_type_id),
      )
      if (!data?.device_names?.length || !igbt) return null
      return {
        data,
        igbt,
        power,
        label: source === 'module' ? 'PCS Module' : 'PCS Module Group',
      }
    }

    const primary = viewSource === 'module' ? moduleData.data : groupData.data
    const result = buildResult(primary, viewSource)
    if (result) return result

    const fallback = viewSource === 'module' ? groupData.data : moduleData.data
    return buildResult(
      fallback,
      viewSource === 'module' ? 'module_group' : 'module',
    )
  }, [moduleData, groupData, viewSource])

  const faultInfo =
    viewSource === 'module' ? faultData.module : faultData.moduleGroup

  const barData = useMemo((): Data[] => {
    if (!activeData) return []
    const names = activeData.data.device_names.filter(
      (n): n is string => n !== null,
    )
    const hoverTexts = names.map(
      (name) =>
        faultInfo?.hoverMap.get(name) ??
        '<b>Faults/Errors/Warnings</b><br>None',
    )
    const faultDeviceNames = names.filter((name) =>
      faultInfo?.faultSet.has(name),
    )
    const yVals =
      activeData.igbt.values?.filter((v): v is number => v !== null) || []
    const yBottom = yVals.length > 0 ? Math.min(...yVals) - 5 : -5

    const traces: Data[] = [
      {
        x: names,
        y: activeData.igbt.values?.map((v) => (v !== null ? v : 0)) || [],
        type: 'bar' as const,
        name: 'IGBT Temperature',
        customdata: hoverTexts,
        hovertemplate:
          '<b>%{x}</b><br>IGBT: %{y:.1f}°C<br><br>%{customdata}<extra></extra>',
        marker: { color: '#3498db' },
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

    return traces
  }, [activeData, faultInfo])

  const scatterData = useMemo((): Data[] => {
    if (!activeData?.power) return []
    const names = activeData.data.device_names.filter(
      (n): n is string => n !== null,
    )
    const x: number[] = []
    const y: number[] = []
    const text: string[] = []
    const customdata: string[] = []

    names.forEach((name, idx) => {
      const temp = activeData.igbt.values?.[idx]
      const pwr = activeData.power!.values?.[idx]
      if (temp != null && pwr != null) {
        x.push(pwr as number)
        y.push(temp as number)
        text.push(name)
        customdata.push(
          faultInfo?.hoverMap.get(name) ??
            '<b>Faults/Errors/Warnings</b><br>None',
        )
      }
    })
    if (x.length === 0) return []

    const apparentIds = [
      SensorTypeEnum.BESS_PCS_MODULE_APPARENT_POWER,
      SensorTypeEnum.BESS_PCS_MODULE_GROUP_APPARENT_POWER,
    ]
    const isApparent = apparentIds.includes(
      activeData.power!.sensor_type_id as (typeof apparentIds)[number],
    )
    const label = isApparent ? 'Apparent Power' : 'Active Power'

    return [
      {
        x,
        y,
        text,
        customdata,
        type: 'scatter' as const,
        mode: 'markers' as const,
        name: `${label} vs IGBT Temp`,
        marker: {
          size: 8,
          color: '#3498db',
          opacity: 0.7,
        },
        hovertemplate:
          '%{text}<br>' +
          `${label}: %{x:.2f} MW<br>` +
          'IGBT: %{y:.1f}°C<br><br>%{customdata}' +
          '<extra></extra>',
      } satisfies Data,
    ]
  }, [activeData, faultInfo])

  const powerAxisLabel = useMemo(() => {
    if (!activeData?.power) return 'Power (MW)'
    const apparentIds = [
      SensorTypeEnum.BESS_PCS_MODULE_APPARENT_POWER,
      SensorTypeEnum.BESS_PCS_MODULE_GROUP_APPARENT_POWER,
    ]
    return apparentIds.includes(
      activeData.power.sensor_type_id as (typeof apparentIds)[number],
    )
      ? 'Apparent Power (MVA)'
      : 'Active Power (MWac)'
  }, [activeData])

  const chartTitle = activeData
    ? `IGBT Temperature (${activeData.label})`
    : 'IGBT Temperature'

  const barYAxisRange = useMemo(() => {
    if (!(barData.length > 1 && (faultInfo?.faultSet.size ?? 0) > 0)) {
      return undefined
    }

    const first = barData[0]
    const yVals = first && 'y' in first ? (first.y as number[]) || [] : []
    const valid = yVals.filter((value) => value != null) as number[]
    const min = valid.length ? Math.min(...valid) : 0
    const max = valid.length ? Math.max(...valid) : 100

    return [min - 10, max + 5] as [number, number]
  }, [barData, faultInfo?.faultSet.size])

  const scatterXAxisRange = maxCapacityMWac
    ? ([-maxCapacityMWac, maxCapacityMWac] as [number, number])
    : undefined

  return (
    <CustomCard
      title={chartTitle}
      style={{ height: '400px' }}
      allowMinimize={true}
      storageKey={`bess-pcs-realtime-igbt-${projectId}`}
      headerChildren={
        <Group gap="xs">
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
          <SegmentedControl
            value={viewMode}
            onChange={(v) => setViewMode(v as 'bar' | 'scatter')}
            data={[
              { label: 'Bar Chart', value: 'bar' },
              { label: 'Power vs Temp', value: 'scatter' },
            ]}
            size="xs"
            onClick={(e) => e.stopPropagation()}
          />
        </Group>
      }
    >
      {viewMode === 'bar' ? (
        <PlotlyPlot
          data={barData}
          layout={{
            uirevision: `bess-igbt-bar-${projectId}-${viewSource}`,
            yaxis: {
              title: {
                text: 'Temperature (°C)',
              },
              range: barYAxisRange,
            },
            xaxis: {
              title: {
                text: activeData?.label || 'PCS Module',
              },
            },
          }}
          isLoading={moduleData.isLoading || groupData.isLoading}
          error={moduleData.error || groupData.error}
          noDataMessage="No IGBT temperature data available."
        />
      ) : (
        <PlotlyPlot
          data={scatterData}
          layout={{
            uirevision: `bess-igbt-scatter-${projectId}-${viewSource}`,
            xaxis: {
              title: { text: powerAxisLabel },
              range: scatterXAxisRange,
            },
            yaxis: {
              title: {
                text: 'IGBT Temperature (°C)',
              },
            },
          }}
          isLoading={moduleData.isLoading || groupData.isLoading}
          error={moduleData.error || groupData.error}
          noDataMessage="No IGBT temperature or power data available."
        />
      )}
    </CustomCard>
  )
}
