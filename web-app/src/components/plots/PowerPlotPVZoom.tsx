import { EventLossTypeEnum, ProjectTypeEnum } from '@/api/enumerations'
import {
  type EventLosses5Min,
  type EventLosses5MinGroup,
  type EventLosses5MinSeries,
  useGetEventLosses5Min,
} from '@/api/v1/operational/project/events'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetMeterPowerAndExpectedPower } from '@/api/v1/protected/pv-expected-energy/plot/plot'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { DataTimeSeries, Quality } from '@/hooks/types'
import { getInterval, roundTime } from '@/utils/interval'
import {
  Badge,
  Button,
  Group,
  HoverCard,
  List,
  Menu,
  Space,
  Text,
  ThemeIcon,
  Tooltip,
  rem,
  useMantineTheme,
} from '@mantine/core'
import {
  IconArrowLeft,
  IconArrowRight,
  IconCaretDown,
  IconCheck,
  IconExclamationMark,
  IconLetterQ,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type * as Plotly from 'plotly.js'
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router'

// Extend dayjs with timezone support
dayjs.extend(utc)
dayjs.extend(timezone)

const parseIntervalMinutes = (value: string): number => {
  const match = value.match(/(\d+)/)
  if (!match) {
    return 5
  }
  return Number(match[1])
}

const alignLossSeries = (
  baseTimes: string[],
  lossTimes: string[],
  lossValues: number[],
  targetMinutes: number,
  timezone: string,
): (number | null)[] => {
  if (baseTimes.length === 0 || lossTimes.length === 0) {
    return new Array(baseTimes.length).fill(null)
  }

  const baseMs = baseTimes.map((time) =>
    dayjs(time).tz(timezone, true).valueOf(),
  )
  const losses = lossTimes
    .map((time, idx) => ({
      time: dayjs(time).tz(timezone, true).valueOf(),
      value: lossValues[idx],
    }))
    .sort((a, b) => a.time - b.time)

  const result: (number | null)[] = new Array(baseTimes.length).fill(null)

  if (targetMinutes <= 1) {
    let lossIdx = 0
    let currentValue: number | null = losses[0]?.value ?? null

    for (let i = 0; i < baseMs.length; i += 1) {
      const time = baseMs[i]
      while (lossIdx + 1 < losses.length && time >= losses[lossIdx + 1].time) {
        lossIdx += 1
        currentValue = losses[lossIdx].value
      }

      if (time < losses[0].time) {
        result[i] = null
      } else {
        result[i] = currentValue
      }
    }

    return result
  }

  let pointer = 0
  let lastValue: number | null = null

  for (let i = 0; i < baseMs.length; i += 1) {
    const start = baseMs[i]
    const end =
      i < baseMs.length - 1 ? baseMs[i + 1] : start + targetMinutes * 60 * 1000

    while (pointer < losses.length && losses[pointer].time < start) {
      pointer += 1
    }

    let idx = pointer
    let sum = 0
    let count = 0

    while (idx < losses.length && losses[idx].time < end) {
      sum += losses[idx].value
      count += 1
      idx += 1
    }

    if (count > 0) {
      const average = sum / count
      result[i] = average
      lastValue = average
      pointer = idx
    } else {
      result[i] = lastValue
    }
  }

  return result
}

const isLossSeries = (entry: EventLosses5Min): entry is EventLosses5MinSeries =>
  'losses' in entry

const isLossGroup = (entry: EventLosses5Min): entry is EventLosses5MinGroup =>
  'data' in entry

const PowerPlotPVZoom = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const theme = useMantineTheme()
  const [startTime, setStartTime] = useState<string>(
    dayjs()
      .minute(Math.floor(dayjs().minute() / 5) * 5)
      .second(0)
      .subtract(24, 'hours')
      .toISOString(),
  )
  const [endTime, setEndTime] = useState<string>(
    dayjs()
      .minute(Math.floor(dayjs().minute() / 5) * 5)
      .second(0)
      .toISOString(),
  )
  const [interval, setInterval] = useState<string>('5min')
  const [isAutoUpdating, setIsAutoUpdating] = useState(true) // Track if we should auto-update the range

  const handleDefaultView = () => {
    const newEndTime = dayjs()
      .minute(Math.floor(dayjs().minute() / 5) * 5)
      .second(0)
      .toISOString()
    const newStartTime = dayjs()
      .minute(Math.floor(dayjs().minute() / 5) * 5)
      .second(0)
      .subtract(24, 'hours')
      .toISOString()
    setEndTime(newEndTime)
    setStartTime(newStartTime)
    setInterval(getInterval(newStartTime, newEndTime))
    setIsAutoUpdating(true) // Re-enable auto-update when resetting to default view
  }

  const handleTimeRangeChange = (range: '48h' | '7d' | 'yesterday') => {
    let start = dayjs()
    const end = dayjs()

    if (range === '48h') {
      start = end.subtract(48, 'hours')
      setIsAutoUpdating(true) // Enable auto-update for relative time ranges
    } else if (range === '7d') {
      start = end.subtract(7, 'days')
      setIsAutoUpdating(true) // Enable auto-update for relative time ranges
    } else if (range === 'yesterday') {
      start = dayjs().subtract(1, 'day').startOf('day')
      setIsAutoUpdating(false) // Disable auto-update for "yesterday" view
    }

    setStartTime(start.toISOString())
    setEndTime(end.toISOString())
    setInterval(getInterval(start.toISOString(), end.toISOString()))
  }

  // Color map based on the names returned by the specific hook
  const colorMap: Record<string, string> = {
    'Meter Active Power': theme.colors.green[7],
    'Power Expected at Full Health': theme.colors.orange[7],
    'PPC Active Power Setpoint': theme.colors.blue[7], // Add setpoint color
    'PV Active Power': theme.colors.cyan[7], // Adjusted PV color for distinction
    'BESS Active Power': theme.colors.yellow[7],
    'Interconnection Limit': theme.colors.gray[7],
  }

  const project = useSelectProject(projectId!)

  // Auto-update time range for "last 24 hours" view
  useEffect(() => {
    if (!isAutoUpdating) return

    const updateTimeRange = () => {
      const now = dayjs()
      const newEndTime = now
        .minute(Math.floor(now.minute() / 5) * 5)
        .second(0)
        .toISOString()
      const newStartTime = now
        .minute(Math.floor(now.minute() / 5) * 5)
        .second(0)
        .subtract(24, 'hours')
        .toISOString()

      setEndTime(newEndTime)
      setStartTime(newStartTime)
      setInterval(getInterval(newStartTime, newEndTime))
    }

    // Update immediately
    updateTimeRange()

    // Then update every minute to keep the range current
    const intervalId = window.setInterval(updateTimeRange, 60 * 1000)

    return () => window.clearInterval(intervalId)
  }, [isAutoUpdating])

  // TODO: Remove this in favor of a new database table.
  const includeSoiling = !['sigurd'].includes(project.data?.name_short || '')
  const includeDegradation = ['sigurd'].includes(project.data?.name_short || '')

  // Use the updated useGetMeterPowerAndExpectedPower hook
  const data = useGetMeterPowerAndExpectedPower({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      // Pass start and end times
      start: roundTime(startTime, interval, 'down'),
      end: roundTime(endTime, interval, 'up'),
      interval: interval,
      // Determine include_storage based on project type if needed
      include_storage: project.data?.project_type_id === ProjectTypeEnum.PVS,
      // TODO: Replace 'false' with the correct condition based on project data
      include_setpoint: true, // Placeholder - set based on actual project properties
      include_soiling: includeSoiling,
      include_degradation: includeDegradation,
    },
    queryOptions: {
      enabled: !!project.data && !!startTime && !!endTime,
      refetchOnWindowFocus: false,
      refetchInterval: 60 * 1000, // Refetch every 60 seconds
      staleTime: 30 * 1000, // Consider data stale after 30 seconds
    },
  })

  const eventLosses5Min = useGetEventLosses5Min({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: roundTime(startTime, interval, 'down'),
      end: roundTime(endTime, interval, 'up'),
      event_loss_type_ids: [EventLossTypeEnum.PROXIMAL_ENERGY],
    },
    queryOptions: {
      enabled: !!project.data && !!startTime && !!endTime,
    },
  })

  // Calculate performance index from meter and expected power traces
  const performanceIndex = (() => {
    if (!data.data?.data) return undefined

    let meterTrace: DataTimeSeries | undefined
    switch (project.data?.project_type_id) {
      case ProjectTypeEnum.PV:
        meterTrace = data.data?.data?.find(
          (trace: DataTimeSeries) => trace.name === 'Meter Active Power',
        )
        break
      case ProjectTypeEnum.BESS:
        return undefined
      case ProjectTypeEnum.PVS:
        meterTrace = data.data?.data?.find(
          (trace: DataTimeSeries) => trace.name === 'PV Active Power',
        )
        break
      default:
        return undefined
    }

    // Clip meterTrace values to a minimum of 0
    if (meterTrace) {
      meterTrace = {
        ...meterTrace,
        y: meterTrace.y.map((val) =>
          val !== null ? Math.max(0, val) : null,
        ) as number[],
      }
    }

    const expectedTrace = data.data.data.find(
      (trace: DataTimeSeries) => trace.name === 'Expected Power',
    )

    if (!meterTrace || !expectedTrace) return undefined

    // Sum the y values, filtering out nulls
    const sumMeter = meterTrace.y.reduce(
      (sum: number, val: number | null) => sum + (val ?? 0),
      0,
    )
    const sumExpected = expectedTrace.y.reduce(
      (sum: number, val: number | null) => sum + (val ?? 0),
      0,
    )

    // Convert to MWh based on interval
    // 15min interval: divide by 4 (15 minutes = 1/4 hour)
    // 5min interval: divide by 12 (5 minutes = 1/12 hour)
    // 1min interval: divide by 60 (1 minute = 1/60 hour)
    const conversionFactor =
      interval === '5min'
        ? 12
        : interval === '1min'
          ? 60
          : interval === '15min'
            ? 4
            : 12
    const meterMWh = sumMeter / conversionFactor
    const expectedMWh = sumExpected / 12

    // Calculate performance index
    if (expectedMWh === 0) return undefined
    return meterMWh / expectedMWh
  })()

  const handleRelayout = (event: Readonly<Plotly.PlotRelayoutEvent>) => {
    const newStartTime = event['xaxis.range[0]']
    const newEndTime = event['xaxis.range[1]']

    if (newStartTime && newEndTime) {
      // Convert Plotly time values to proper ISO strings
      // Plotly returns time values as local time strings, but we need to interpret them as project timezone
      const projectTimezone = project.data?.time_zone || 'UTC'

      const newStartTimeStr =
        typeof newStartTime === 'number'
          ? new Date(newStartTime).toISOString()
          : dayjs.tz(String(newStartTime), projectTimezone).utc().toISOString()
      const newEndTimeStr =
        typeof newEndTime === 'number'
          ? new Date(newEndTime).toISOString()
          : dayjs.tz(String(newEndTime), projectTimezone).utc().toISOString()

      const currentStart = dayjs(startTime)
      const currentEnd = dayjs(endTime)
      const newStart = dayjs(newStartTimeStr)
      const newEnd = dayjs(newEndTimeStr)

      if (
        Math.abs(currentStart.diff(newStart, 'minute')) > 1 ||
        Math.abs(currentEnd.diff(newEnd, 'minute')) > 1
      ) {
        setStartTime(newStartTimeStr)
        setEndTime(newEndTimeStr)
        setInterval(getInterval(newStartTimeStr, newEndTimeStr))
        setIsAutoUpdating(false) // Disable auto-update when user manually zooms
      }
    }
  }

  const handlePan = (direction: 'left' | 'right') => {
    const range = dayjs(endTime).diff(dayjs(startTime), 'minute')
    const newStartTime =
      direction === 'left'
        ? dayjs(startTime).subtract(range, 'minute').toISOString()
        : dayjs(startTime).add(range, 'minute').toISOString()
    const newEndTime =
      direction === 'left'
        ? dayjs(endTime).subtract(range, 'minute').toISOString()
        : dayjs(endTime).add(range, 'minute').toISOString()
    setStartTime(newStartTime)
    setEndTime(newEndTime)
    setIsAutoUpdating(false) // Disable auto-update when user manually pans
  }

  const firstLossEntry = eventLosses5Min.data?.[0]
  const lossesSeries: EventLosses5MinSeries | undefined = useMemo(() => {
    if (!firstLossEntry) {
      return undefined
    }
    if (isLossSeries(firstLossEntry)) {
      return firstLossEntry
    }
    if (isLossGroup(firstLossEntry) && Array.isArray(firstLossEntry.data)) {
      return firstLossEntry.data[0]
    }
    return undefined
  }, [firstLossEntry])

  const lossesGroupLabel = useMemo(() => {
    if (!firstLossEntry || !isLossGroup(firstLossEntry)) {
      return null
    }
    return (
      firstLossEntry.device_id ??
      firstLossEntry.device_type_id ??
      firstLossEntry.failure_mode_id ??
      firstLossEntry.root_cause_id ??
      null
    )
  }, [firstLossEntry])

  // Map data from the MeterPowerAndExpected type

  const projectTimeZone = project.data?.time_zone ?? 'UTC'

  const baseSeriesName = useMemo(() => {
    switch (project.data?.project_type_id) {
      case ProjectTypeEnum.PV:
        return 'Meter Active Power'
      case ProjectTypeEnum.PVS:
        return 'PV Active Power'
      default:
        return null
    }
  }, [project.data?.project_type_id])

  const baseSeries =
    baseSeriesName && data.data?.data
      ? data.data.data.find(
          (trace: DataTimeSeries) => trace.name === baseSeriesName,
        )
      : undefined

  const baseTimesNormalized =
    baseSeries && Array.isArray(baseSeries.x)
      ? (baseSeries.x as (string | number | Date)[]).map((value) => {
          if (typeof value === 'string') {
            return value
          }
          if (typeof value === 'number') {
            return new Date(value).toISOString()
          }
          return value.toISOString()
        })
      : undefined

  const alignedLossValues = useMemo<(number | null)[] | null>(() => {
    if (!baseTimesNormalized || !lossesSeries) {
      return null
    }
    const targetMinutes = parseIntervalMinutes(interval)
    return alignLossSeries(
      baseTimesNormalized,
      lossesSeries.losses.time,
      lossesSeries.losses.loss,
      targetMinutes,
      projectTimeZone,
    )
  }, [baseTimesNormalized, lossesSeries, interval, projectTimeZone])

  const hasStackedLosses =
    project.data?.project_type_id !== ProjectTypeEnum.BESS &&
    alignedLossValues !== null &&
    alignedLossValues.some((value) => value !== null)

  const plotData = data.data?.data.map((d: DataTimeSeries) => {
    const numericY = d.y.map((val: number | null) =>
      val === null ? null : parseFloat(String(val)),
    )

    // Transform name if it's "Expected Power" from backend
    const displayName =
      d.name === 'Expected Power' ? 'Power Expected at Full Health' : d.name

    // Determine mode and fill based on trace name
    const isMeterPower = displayName === 'Meter Active Power'
    const isSetpoint = displayName === 'PPC Active Power Setpoint'
    const isExpectedPower = displayName === 'Power Expected at Full Health' // Check for Expected Power
    const isPvActivePower = displayName === 'PV Active Power'
    const isStackBase =
      (project.data?.project_type_id === ProjectTypeEnum.PV && isMeterPower) ||
      (project.data?.project_type_id === ProjectTypeEnum.PVS && isPvActivePower)
    const mode =
      isMeterPower || isSetpoint || isExpectedPower ? 'lines' : 'lines+markers' // Set mode to lines for Meter, Setpoint, and Expected Power
    const fill = isStackBase ? 'tozeroy' : 'none' // Only fill for meter
    const stackgroup = isStackBase && hasStackedLosses ? 'power' : undefined

    return {
      x: d.x,
      y: numericY,
      name: displayName,
      type: 'scatter' as const,
      mode: mode, // Use determined mode
      connectgaps: isExpectedPower ? false : true,
      hoverlabel: {
        namelength: -1,
      },
      fill: fill, // Use determined fill
      line: {
        color:
          colorMap[displayName as keyof typeof colorMap] ||
          theme.colors.gray[7],
        width: 2,
      },
      stackgroup,
      marker: {
        // Only show markers if mode includes them
        size: mode.includes('markers') ? 4 : 0,
        // Ensure setpoint markers are hidden even if mode logic changes
        opacity: isSetpoint ? 0 : 1,
      },
      visible: true,
    }
  }) as Partial<Plotly.Data>[] | undefined

  // Add interconnection limit trace if we have project data and plot data
  if (
    plotData &&
    project.data?.poi &&
    data.data?.data &&
    data.data.data.length > 0
  ) {
    const firstTrace = data.data.data[0]
    plotData.push({
      x: firstTrace.x,
      y: Array(firstTrace.x.length).fill(project.data.poi),
      name: 'Interconnection Limit',
      type: 'scatter' as const,
      mode: 'lines',
      line: {
        color: colorMap['Interconnection Limit'],
        width: 2,
        dash: 'dash',
      },
      hoverlabel: {
        namelength: -1,
      },
      visible: true,
    })
  }

  if (
    plotData &&
    alignedLossValues !== null &&
    baseTimesNormalized &&
    hasStackedLosses
  ) {
    plotData.push({
      x: baseTimesNormalized,
      y: alignedLossValues,
      name:
        lossesGroupLabel != null
          ? `Event Losses - Device ${lossesGroupLabel}`
          : 'Event Losses',
      type: 'scatter',
      mode: 'lines',
      line: { color: theme.colors.gray[5] },
      fill: 'tonexty',
      fillcolor: theme.colors.gray[2],
      stackgroup: 'power',
      hoverlabel: { namelength: -1 },
    })
  }

  return (
    <CustomCard
      title="Meter Power"
      // Quality data might be available again at data.data.quality
      quality={
        data.data?.quality && <QualityCard quality={data.data.quality} />
      }
      style={{ flex: 2 }}
      headerChildren={
        <Group wrap="nowrap">
          {performanceIndex !== undefined && (
            <Tooltip label="Performance Index for the plotted period: metered energy divided by expected energy at full health.">
              <Badge
                size="lg"
                color={
                  performanceIndex < 1.11
                    ? performanceIndex > 0.9
                      ? 'green'
                      : performanceIndex > 0.5
                        ? 'yellow'
                        : 'red'
                    : 'gray'
                }
              >
                {performanceIndex < 1.11
                  ? `P.I. ${(performanceIndex * 100).toFixed(1) + '%'}`
                  : 'P.I. >110%'}
              </Badge>
            </Tooltip>
          )}
          <Tooltip label="Pan Left">
            <Button size="xs" variant="light" onClick={() => handlePan('left')}>
              <IconArrowLeft />
            </Button>
          </Tooltip>
          <Button.Group>
            <Tooltip label="Reset to the last 24 hours. You can also zoom by scrolling.">
              <Button size="xs" variant="light" onClick={handleDefaultView}>
                Last 24 Hours
              </Button>
            </Tooltip>
            <Menu>
              <Menu.Target>
                <Tooltip label="Select a time range">
                  <Button size="xs" variant="light">
                    <IconCaretDown />
                  </Button>
                </Tooltip>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item onClick={() => handleTimeRangeChange('yesterday')}>
                  Yesterday
                </Menu.Item>
                <Menu.Item onClick={() => handleTimeRangeChange('48h')}>
                  Last 48 Hours
                </Menu.Item>
                <Menu.Item onClick={() => handleTimeRangeChange('7d')}>
                  Last 7 Days
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Button.Group>
          <Tooltip label="Pan Right">
            <Button
              size="xs"
              variant="light"
              onClick={() => handlePan('right')}
            >
              <IconArrowRight />
            </Button>
          </Tooltip>
        </Group>
      }
    >
      <PlotlyPlot
        data={plotData}
        layout={
          project.data && {
            yaxis: {
              title: { text: 'Power (MW)' },
              fixedrange: true,
              // Restore explicit range
              range:
                project.data?.project_type_id === ProjectTypeEnum.PVS
                  ? undefined
                  : [0, project.data.poi * 1.05],
            },
            xaxis: {
              type: 'date',
              fixedrange: false,
              tickangle: 0,
            },
          }
        }
        onRelayout={handleRelayout}
        // Use the loading state from the hook
        isLoading={data.isLoading || project.isLoading}
        error={data.error}
        config={{ responsive: true, scrollZoom: true }}
      />
    </CustomCard>
  )
}

function QualityCard({ quality }: { quality: Quality }) {
  const theme = useMantineTheme() // Need theme here too
  const colorMap = {
    good: theme.colors.green[7],
    warning: theme.colors.yellow[7],
    bad: theme.colors.red[7],
  }

  const iconMap = {
    good: <IconCheck style={{ width: rem(16), height: rem(16) }} />,
    warning: (
      <IconExclamationMark style={{ width: rem(16), height: rem(16) }} />
    ),
    bad: <IconExclamationMark style={{ width: rem(16), height: rem(16) }} />,
  }

  return (
    <HoverCard shadow="md">
      <HoverCard.Target>
        <ThemeIcon color={colorMap[quality.level]} size={20} radius="xl">
          <IconLetterQ style={{ width: rem(16), height: rem(16) }} />
        </ThemeIcon>
      </HoverCard.Target>
      <HoverCard.Dropdown>
        <Text>{quality.message}</Text>
        <Space h="xs" />
        <List spacing="xs" size="sm" center>
          {quality.details.map((detail, i) => (
            <List.Item
              key={i}
              icon={
                <ThemeIcon color={colorMap[detail.level]} size={20} radius="xl">
                  {iconMap[detail.level]}
                </ThemeIcon>
              }
            >
              {detail.message}
            </List.Item>
          ))}
        </List>
      </HoverCard.Dropdown>
    </HoverCard>
  )
}

export default PowerPlotPVZoom
