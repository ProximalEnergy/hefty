import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { DataTimeSeries } from '@/hooks/types'
import { Skeleton, Stack, useMantineTheme } from '@mantine/core'
import type { Data, Layout } from 'plotly.js'
import { useMemo } from 'react'

type MetStationWindRoseProps = {
  title: string
  flex: number
  windDirectionData: DataTimeSeries[]
  windSpeedData: DataTimeSeries[]
  isLoading: boolean
}

const DIRECTION_LABELS = [
  'N',
  'NNE',
  'NE',
  'ENE',
  'E',
  'ESE',
  'SE',
  'SSE',
  'S',
  'SSW',
  'SW',
  'WSW',
  'W',
  'WNW',
  'NW',
  'NNW',
]

const SPEED_BUCKETS = [
  { label: '0-2m/s', min: 0, max: 2 },
  { label: '2-4m/s', min: 2, max: 4 },
  { label: '4-6m/s', min: 4, max: 6 },
  { label: '6-8m/s', min: 6, max: 8 },
  { label: '8+m/s', min: 8, max: Number.POSITIVE_INFINITY },
]

const normalizeDirection = (direction: number) => {
  const normalized = direction % 360
  return normalized < 0 ? normalized + 360 : normalized
}

const getDirectionIndex = (direction: number) => {
  const sliceSize = 360 / DIRECTION_LABELS.length
  return (
    Math.floor((normalizeDirection(direction) + sliceSize / 2) / sliceSize) %
    DIRECTION_LABELS.length
  )
}

const getSpeedBucketIndex = (speed: number) => {
  return SPEED_BUCKETS.findIndex((bucket) => {
    return speed >= bucket.min && speed < bucket.max
  })
}

const buildSpeedLookup = (windSpeedData: DataTimeSeries[]) => {
  const speedByDeviceAndTime = new Map<string, number>()
  const speedByTime = new Map<string, number[]>()

  for (const trace of windSpeedData) {
    const pointCount = Math.min(trace.x.length, trace.y.length)
    for (let i = 0; i < pointCount; i += 1) {
      const time = trace.x[i]
      const speed = trace.y[i]
      if (!Number.isFinite(speed)) {
        continue
      }

      speedByDeviceAndTime.set(`${trace.device_id}-${time}`, speed)
      const timeSpeeds = speedByTime.get(time)
      if (timeSpeeds == null) {
        speedByTime.set(time, [speed])
      } else {
        timeSpeeds.push(speed)
      }
    }
  }

  return { speedByDeviceAndTime, speedByTime }
}

const getSpeedForDirectionPoint = ({
  deviceId,
  time,
  speedByDeviceAndTime,
  speedByTime,
}: {
  deviceId: number
  time: string
  speedByDeviceAndTime: Map<string, number>
  speedByTime: Map<string, number[]>
}) => {
  const deviceSpeed = speedByDeviceAndTime.get(`${deviceId}-${time}`)
  if (deviceSpeed != null) {
    return deviceSpeed
  }

  const timeSpeeds = speedByTime.get(time)
  if (timeSpeeds == null || timeSpeeds.length !== 1) {
    return null
  }

  return timeSpeeds[0]
}

export function MetStationWindRose({
  title,
  flex,
  windDirectionData,
  windSpeedData,
  isLoading,
}: MetStationWindRoseProps) {
  const theme = useMantineTheme()

  const plotData = useMemo(() => {
    const countsBySpeedAndDirection = SPEED_BUCKETS.map(() =>
      Array(DIRECTION_LABELS.length).fill(0),
    )
    let totalCount = 0
    const { speedByDeviceAndTime, speedByTime } =
      buildSpeedLookup(windSpeedData)

    for (const trace of windDirectionData) {
      const pointCount = Math.min(trace.x.length, trace.y.length)
      for (let i = 0; i < pointCount; i += 1) {
        const direction = trace.y[i]
        if (!Number.isFinite(direction)) {
          continue
        }

        const speed = getSpeedForDirectionPoint({
          deviceId: trace.device_id,
          time: trace.x[i],
          speedByDeviceAndTime,
          speedByTime,
        })
        if (speed == null || !Number.isFinite(speed)) {
          continue
        }

        const speedBucketIndex = getSpeedBucketIndex(speed)
        if (speedBucketIndex === -1) {
          continue
        }

        countsBySpeedAndDirection[speedBucketIndex][
          getDirectionIndex(direction)
        ] += 1
        totalCount += 1
      }
    }

    if (totalCount === 0) {
      return []
    }

    return SPEED_BUCKETS.map((bucket, index): Data => {
      return {
        type: 'barpolar',
        name: bucket.label,
        theta: DIRECTION_LABELS,
        r: countsBySpeedAndDirection[index].map(
          (count) => (count / totalCount) * 100,
        ),
        marker: {
          color: theme.colors[theme.primaryColor][index + 3],
        },
        hovertemplate:
          'Direction: %{theta}<br>' +
          `Speed: ${bucket.label}<br>` +
          'Frequency: %{r:.1f}%<extra></extra>',
      }
    })
  }, [theme.colors, theme.primaryColor, windDirectionData, windSpeedData])

  const plotLayout: Partial<Layout> = {
    barmode: 'stack',
    hovermode: 'closest',
    margin: { b: 35, l: 35, r: 35, t: 10 },
    polar: {
      angularaxis: {
        direction: 'clockwise',
        rotation: 90,
      },
      radialaxis: {
        ticksuffix: '%',
      },
    },
    showlegend: true,
  }

  return (
    <CustomCard title={title} style={{ flex }}>
      <Stack h="100%">
        {isLoading ? (
          <Skeleton h="100%">
            <PlotlyPlot />
          </Skeleton>
        ) : (
          <PlotlyPlot
            data={plotData}
            layout={plotLayout}
            noDataMessage="No paired wind speed and direction data available."
          />
        )}
      </Stack>
    </CustomCard>
  )
}
