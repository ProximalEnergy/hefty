import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { DataTimeSeries } from '@/hooks/types'
import {
  Skeleton,
  Stack,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import type { Data } from 'plotly.js'
import { useMemo } from 'react'

type MetStationTimeseriesProps = {
  title: string
  flex: number
  data: DataTimeSeries[]
  isLoading: boolean
  average: boolean
}

export function MetStationTimeseries({
  title,
  flex,
  data,
  isLoading,
  average,
}: MetStationTimeseriesProps) {
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme('dark')

  const plotData = useMemo(() => {
    if (!average || data.length === 0) {
      return data as Data[]
    }

    const aggregateByTime = new Map<string, { sum: number; count: number }>()
    for (const trace of data) {
      const pointCount = Math.min(trace.x.length, trace.y.length)
      for (let i = 0; i < pointCount; i += 1) {
        const time = trace.x[i]
        const value = trace.y[i]
        if (!Number.isFinite(value)) {
          continue
        }
        const existing = aggregateByTime.get(time)
        if (existing == null) {
          aggregateByTime.set(time, { sum: value, count: 1 })
        } else {
          existing.sum += value
          existing.count += 1
        }
      }
    }

    const averageX: string[] = []
    const averageY: number[] = []
    for (const [time, agg] of aggregateByTime.entries()) {
      averageX.push(time)
      averageY.push(agg.sum / agg.count)
    }

    const primaryColor = theme.colors[theme.primaryColor][6]
    const dimmedGray =
      colorScheme === 'dark' ? 'rgba(173,181,189,0.22)' : 'rgba(73,80,87,0.22)'

    const individualTraces: Data[] = data.map((trace) => ({
      ...trace,
      line: { color: dimmedGray },
      marker: { color: dimmedGray },
      opacity: 0.3,
    }))

    const averageTrace: Data = {
      x: averageX,
      y: averageY,
      name: 'Average',
      yaxis: data[0]?.yaxis ?? 'y',
      type: 'scatter',
      mode: 'lines',
      line: { color: primaryColor, width: 2.5 },
      opacity: 1,
    }

    return [...individualTraces, averageTrace]
  }, [average, colorScheme, data, theme.colors, theme.primaryColor])

  return (
    <CustomCard title={title} style={{ flex }}>
      <Stack h="100%">
        {isLoading ? (
          <Skeleton h="100%">
            <PlotlyPlot />
          </Skeleton>
        ) : (
          <PlotlyPlot data={plotData} layout={{}} />
        )}
      </Stack>
    </CustomCard>
  )
}
