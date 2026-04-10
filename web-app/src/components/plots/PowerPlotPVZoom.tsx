import {
  EventLossTypeEnum,
  ProjectTypeEnum,
  SensorTypeEnum,
} from '@/api/enumerations'
import {
  type EventLosses5Min,
  type EventLosses5MinGroup,
  type EventLosses5MinSeries,
  useGetEventLosses5Min,
} from '@/api/v1/operational/project/events'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetMeterPowerAndExpectedPowerV3 } from '@/api/v1/protected/system'
import CustomCard from '@/components/CustomCard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { DataTimeSeries } from '@/hooks/types'
import { alignLossSeries, parseIntervalMinutes } from '@/utils/alignLossSeries'
import { getInterval, roundTime } from '@/utils/interval'
import {
  Badge,
  Button,
  Group,
  Menu,
  Tooltip,
  useMantineTheme,
} from '@mantine/core'
import {
  IconArrowLeft,
  IconArrowRight,
  IconCaretDown,
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
  const colorMap: Record<number, string> = {
    [SensorTypeEnum.METER_ACTIVE_POWER]: theme.colors.green[7],
    [SensorTypeEnum.PV_EXPECTED_POWER]: theme.colors.orange[7],
    [SensorTypeEnum.PPC_ACTIVE_POWER_SETPOINT]: theme.colors.blue[7], // Add setpoint color
    [SensorTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER]:
      theme.colors.cyan[7], // Adjusted PV color for distinction
    [SensorTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER]:
      theme.colors.yellow[7],
    [-1]: theme.colors.gray[7],
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

  // Use the updated useGetMeterPowerAndExpectedPowerV3 hook
  const meterAndExpectedPower = useGetMeterPowerAndExpectedPowerV3({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      // Pass start and end times
      start: roundTime(startTime, interval, 'down'),
      end: roundTime(endTime, interval, 'up'),
      interval: interval,
      include_storage: project.data?.project_type_id === ProjectTypeEnum.PVS,
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
    if (!meterAndExpectedPower.data) return undefined

    let meterTrace: DataTimeSeries | undefined
    switch (project.data?.project_type_id) {
      case ProjectTypeEnum.PV:
        meterTrace = meterAndExpectedPower.data.find(
          (trace) => trace.sensor_type_id === SensorTypeEnum.METER_ACTIVE_POWER,
        ) as DataTimeSeries | undefined
        break
      case ProjectTypeEnum.BESS:
        return undefined
      case ProjectTypeEnum.PVS:
        meterTrace = meterAndExpectedPower.data.find(
          (trace) =>
            trace.sensor_type_id ===
            SensorTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER,
        ) as DataTimeSeries | undefined
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

    const expectedTrace = meterAndExpectedPower.data.find(
      (trace) => trace.sensor_type_id === SensorTypeEnum.PV_EXPECTED_POWER,
    ) as DataTimeSeries | undefined

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

  const baseSeriesSensorTypeId = useMemo(() => {
    switch (project.data?.project_type_id) {
      case ProjectTypeEnum.PV:
        return SensorTypeEnum.METER_ACTIVE_POWER
      case ProjectTypeEnum.PVS:
        return SensorTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER
      default:
        return null
    }
  }, [project.data?.project_type_id])

  const baseSeries =
    baseSeriesSensorTypeId && meterAndExpectedPower.data
      ? (meterAndExpectedPower.data.find(
          (trace) => trace.sensor_type_id === baseSeriesSensorTypeId,
        ) as DataTimeSeries | undefined)
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

  const plotData = meterAndExpectedPower.data?.map((trace) => {
    const d = trace as DataTimeSeries
    const numericY = d.y.map((val: number | null) =>
      val === null ? null : parseFloat(String(val)),
    )

    // Transform name for PV Expected Power
    const displayName =
      d.sensor_type_id === SensorTypeEnum.PV_EXPECTED_POWER
        ? 'Power Expected at Full Health'
        : d.name

    // Determine mode and fill based on trace name
    const isMeterPower = d.sensor_type_id === SensorTypeEnum.METER_ACTIVE_POWER
    const isSetpoint =
      d.sensor_type_id === SensorTypeEnum.PPC_ACTIVE_POWER_SETPOINT
    const isExpectedPower =
      d.sensor_type_id === SensorTypeEnum.PV_EXPECTED_POWER
    const isPvActivePower =
      d.sensor_type_id ===
      SensorTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER
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
        color: colorMap[d.sensor_type_id] || theme.colors.gray[7],
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
    meterAndExpectedPower.data &&
    meterAndExpectedPower.data.length > 0
  ) {
    const firstTrace = meterAndExpectedPower.data[0]
    plotData.push({
      x: firstTrace.x,
      y: Array(firstTrace.x.length).fill(project.data.poi),
      name: 'Interconnection Limit',
      type: 'scatter' as const,
      mode: 'lines',
      line: {
        color: colorMap[-1],
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

  let performanceIndexBadgeColor: 'gray' | 'green' | 'yellow' | 'red' = 'gray'
  let performanceIndexBadgeText = ''
  if (performanceIndex !== undefined) {
    performanceIndexBadgeText =
      performanceIndex < 1.11
        ? `P.I. ${(performanceIndex * 100).toFixed(1)}%`
        : 'P.I. >110%'
    performanceIndexBadgeColor =
      performanceIndex < 1.11
        ? performanceIndex > 0.9
          ? 'green'
          : performanceIndex > 0.5
            ? 'yellow'
            : 'red'
        : 'gray'
  }

  const meterPowerPlotLayout: Partial<Plotly.Layout> | undefined = project.data
    ? {
        yaxis: {
          title: { text: 'Power (MW)' },
          fixedrange: true,
          range:
            project.data.project_type_id === ProjectTypeEnum.PVS
              ? undefined
              : [0, project.data.poi * 1.05],
        },
        xaxis: {
          type: 'date',
          fixedrange: false,
          tickangle: 0,
        },
      }
    : undefined

  return (
    <CustomCard
      title="Meter Power"
      style={{ flex: 2 }}
      headerChildren={
        <Group wrap="nowrap">
          {performanceIndex !== undefined && (
            <Tooltip label="Performance Index for the plotted period: metered energy divided by expected energy at full health.">
              <Badge size="lg" color={performanceIndexBadgeColor}>
                {performanceIndexBadgeText}
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
        xAxisTimeZone={projectTimeZone}
        layout={meterPowerPlotLayout}
        onRelayout={handleRelayout}
        // Use the loading state from the hook
        isLoading={meterAndExpectedPower.isLoading || project.isLoading}
        error={meterAndExpectedPower.error}
        config={{ responsive: true, scrollZoom: false }}
      />
    </CustomCard>
  )
}

export default PowerPlotPVZoom
