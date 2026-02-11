import { useGetPTPData } from '@/api/v1/protected/web-application/projects/financial/ptp_data'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { Skeleton, Stack, Text, useMantineTheme } from '@mantine/core'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type { Layout, PlotData } from 'plotly.js'
import { useMemo } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)

type PlotTrace = Partial<PlotData> & {
  y?: Array<number | null>
}

/** PTP API response shape for SPP profile data. */
interface SppDataPoint {
  keyName?: string
  values?: SppValueItem[]
}
interface SppValueItem {
  intervalStartUtc?: string
  data?: Array<{ value?: number }>
}
interface SppElement {
  dataPoints?: SppDataPoint[]
}
interface SppResponse {
  data?: SppElement[]
}

type Percentiles = {
  p10: number | null
  p50: number | null
  p90: number | null
}

function quantile(values: number[], q: number): number | null {
  if (values.length === 0) return null
  const sorted = [...values].sort((a, b) => a - b)
  const pos = (sorted.length - 1) * q
  const base = Math.floor(pos)
  const rest = pos - base
  const lower = sorted[base]
  const upper = sorted[Math.min(base + 1, sorted.length - 1)]
  return lower + rest * (upper - lower)
}

function computeHourPercentiles(values: number[]): Percentiles {
  return {
    p10: quantile(values, 0.1),
    p50: quantile(values, 0.5),
    p90: quantile(values, 0.9),
  }
}

function rgbaFromHex(hex: string, alpha: number): string {
  const safe = hex.startsWith('#') ? hex.slice(1) : hex
  const r = parseInt(safe.slice(0, 2), 16)
  const g = parseInt(safe.slice(2, 4), 16)
  const b = parseInt(safe.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function hourLabels(): string[] {
  return Array.from(
    { length: 24 },
    (_, h) => `${String(h).padStart(2, '0')}:00`,
  )
}

function extractSeries({
  data,
  keyName,
  tz,
}: {
  data: unknown
  keyName: 'DASPP' | 'RTSPP'
  tz: string
}): Map<number, number[]> {
  const buckets = new Map<number, number[]>()
  for (let i = 0; i < 24; i++) buckets.set(i, [])

  const payload = data as SppResponse
  if (!payload || typeof payload !== 'object' || !Array.isArray(payload.data)) {
    return buckets
  }

  const elements = payload.data
  const element =
    elements.find((el: SppElement) =>
      Array.isArray(el?.dataPoints)
        ? el.dataPoints.some(
            (dp: SppDataPoint) =>
              dp?.keyName === 'DASPP' || dp?.keyName === 'RTSPP',
          )
        : false,
    ) ?? elements[0]

  const dataPoints = Array.isArray(element?.dataPoints)
    ? element.dataPoints
    : []
  const dp = dataPoints.find((d: SppDataPoint) => d?.keyName === keyName)
  const values = Array.isArray(dp?.values) ? dp.values : []

  values.forEach((v: SppValueItem) => {
    const rawTs = v?.intervalStartUtc
    const rawVal = v?.data?.[0]?.value
    const num = typeof rawVal === 'number' ? rawVal : Number(rawVal)
    if (!rawTs || !Number.isFinite(num)) return

    const hour = dayjs.utc(rawTs).tz(tz).hour()
    buckets.get(hour)?.push(num)
  })

  return buckets
}

export function SppDailyProfileCard({
  projectId,
  projectTimeZone,
  startDate,
  endDate,
}: {
  projectId: string
  projectTimeZone?: string | null
  startDate: Date | null
  endDate: Date | null
}) {
  const theme = useMantineTheme()

  const { data, isLoading } = useGetPTPData({
    pathParams: { projectId },
    queryParams: {
      endpoint: 'Market-Prices',
      category: 'market',
      start: startDate ? dayjs.utc(startDate).toISOString() : undefined,
      end: endDate ? dayjs.utc(endDate).toISOString() : undefined,
      data_points: ['DASPP', 'RTSPP'],
    },
    queryOptions: {
      enabled: !!projectId && !!projectTimeZone && !!startDate && !!endDate,
      staleTime: 5 * 60 * 1000,
    },
  })

  const { traces, layout, isEmpty } = useMemo(() => {
    if (!projectTimeZone) {
      return {
        traces: [] as PlotTrace[],
        layout: {} as Partial<Layout>,
        isEmpty: true,
      }
    }

    const daBuckets = extractSeries({
      data,
      keyName: 'DASPP',
      tz: projectTimeZone,
    })
    const rtBuckets = extractSeries({
      data,
      keyName: 'RTSPP',
      tz: projectTimeZone,
    })

    const x = hourLabels()

    const daStats = Array.from({ length: 24 }, (_, h) =>
      computeHourPercentiles(daBuckets.get(h) ?? []),
    )
    const rtStats = Array.from({ length: 24 }, (_, h) =>
      computeHourPercentiles(rtBuckets.get(h) ?? []),
    )

    const daColor = theme.colors.blue[6]
    const rtColor = theme.colors.orange[6]

    const daP10 = daStats.map((s) => s.p10)
    const daP90 = daStats.map((s) => s.p90)
    const daP50 = daStats.map((s) => s.p50)

    const rtP10 = rtStats.map((s) => s.p10)
    const rtP90 = rtStats.map((s) => s.p90)
    const rtP50 = rtStats.map((s) => s.p50)

    const hasAnyDa = daP50.some((v) => v !== null)
    const hasAnyRt = rtP50.some((v) => v !== null)

    const traces: PlotTrace[] = [
      // DA band (P10..P90)
      {
        x,
        y: daP10,
        type: 'scatter',
        mode: 'lines',
        line: { color: daColor, width: 1, dash: 'dash' },
        hoverinfo: 'skip',
        showlegend: false,
        name: 'DA P10',
      },
      {
        x,
        y: daP90,
        type: 'scatter',
        mode: 'lines',
        line: { color: daColor, width: 1, dash: 'dash' },
        fill: 'tonexty',
        fillcolor: rgbaFromHex(daColor, 0.18),
        hoverinfo: 'skip',
        showlegend: false,
        name: 'DA P90',
      },
      {
        x,
        y: daP50,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'DA Median (P50)',
        line: { color: daColor, width: 3 },
        marker: { color: daColor, size: 5 },
        hovertemplate:
          '<b>DA Median</b><br>%{x}: %{y:.2f} $/MWh<extra></extra>',
      },
      // RT band (P10..P90)
      {
        x,
        y: rtP10,
        type: 'scatter',
        mode: 'lines',
        line: { color: rtColor, width: 1, dash: 'dash' },
        hoverinfo: 'skip',
        showlegend: false,
        name: 'RT P10',
      },
      {
        x,
        y: rtP90,
        type: 'scatter',
        mode: 'lines',
        line: { color: rtColor, width: 1, dash: 'dash' },
        fill: 'tonexty',
        fillcolor: rgbaFromHex(rtColor, 0.14),
        hoverinfo: 'skip',
        showlegend: false,
        name: 'RT P90',
      },
      {
        x,
        y: rtP50,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'RT Median (P50)',
        line: { color: rtColor, width: 3 },
        marker: { color: rtColor, size: 5 },
        hovertemplate:
          '<b>RT Median</b><br>%{x}: %{y:.2f} $/MWh<extra></extra>',
      },
    ]

    const layout: Partial<Layout> = {
      title: {
        text: 'Profile - Day-Ahead & Real-Time Energy SPP',
        font: { size: 18 },
      },
      xaxis: { title: { text: 'Hour (Local Time)' }, type: 'category' },
      yaxis: { title: { text: '$/MWh' } },
      hovermode: 'x unified',
      legend: { orientation: 'h', y: -0.2 },
      margin: { t: 50, r: 20, l: 60, b: 60 },
    }

    return {
      traces,
      layout,
      isEmpty: !(hasAnyDa || hasAnyRt),
    }
  }, [data, projectTimeZone, theme])

  return (
    <CustomCard title="Average Day SPP Profile (P10–P90 band)">
      {isLoading ? (
        <Skeleton height={420} radius="md" />
      ) : isEmpty ? (
        <Stack gap="xs" py="xl">
          <Text c="dimmed" ta="center">
            No DASPP/RTSPP data available for the selected range.
          </Text>
        </Stack>
      ) : (
        <PlotlyPlot
          data={traces}
          layout={layout}
          isLoading={isLoading}
          error={null}
        />
      )}
    </CustomCard>
  )
}
