import { KPITypeEnum, ProjectTypeEnum } from '@/api/enumerations'
import { useGetUserFavoriteKPITypes } from '@/api/v1/admin/user_kpi_types'
import {
  useGetContractKPIs,
  useGetOperationalKPIData,
} from '@/api/v1/operational/kpi_data'
import { useGetKPIInstances } from '@/api/v1/operational/kpi_instances'
import { useGetKPISummaryCards } from '@/api/v1/operational/project/kpi_data'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { useGetUserProjectLabelsByProjectId } from '@/api/v1/operational/project/project_user_project_labels'
import {
  Project,
  useGetProjects,
  useSelectProject,
} from '@/api/v1/operational/projects'
import { useGetQSEAccess } from '@/api/v1/protected/web-application/projects/financial/qse_access'
import CustomCard, { iconSize, iconStroke } from '@/components/CustomCard'
import DeviceTypeOverview from '@/components/DeviceTypeOverview'
import { PageError } from '@/components/Error'
import KPICard, { EmptyKPICard } from '@/components/KPICard'
import { PageLoader } from '@/components/Loading'
import WeatherCard from '@/components/WeatherCard'
import ProjectInfoModal from '@/components/modals/ProjectInfoModal'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { MarketStatsGrid } from '@/components/stats/MarketStatsGrid'
import { getKPIThresholdbyDate } from '@/pages/projects/kpis/ProjectKPIHome.utils'
import { getInterval, roundTime } from '@/utils/interval'
import { projectDescription } from '@/utils/projectDescription'
import { QUERY_TIME } from '@/utils/queryTiming'
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Center,
  Grid,
  Group,
  List,
  LoadingOverlay,
  Menu,
  Modal,
  ScrollArea,
  SegmentedControl,
  Skeleton,
  Stack,
  Switch,
  Table,
  Text,
  Title,
  Tooltip,
  useMantineTheme,
} from '@mantine/core'
import { useElementSize } from '@mantine/hooks'
import {
  IconActivity,
  IconArrowLeft,
  IconArrowRight,
  IconCaretDown,
  IconChevronDown,
  IconChevronUp,
  IconCursorText,
  IconInfoCircle,
  IconLock,
  IconMouse,
  IconRepeat,
  IconRepeatOff,
  IconSatellite,
  IconZoomIn,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type { Data } from 'plotly.js'
import { PlotRelayoutEvent } from 'plotly.js'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { TopEventsTableCard } from './TopEventsTableCard'
import AdaptiveGisBESS from './gis/adaptive-gis-bess'

// Extend dayjs with timezone support
dayjs.extend(utc)
dayjs.extend(timezone)

const PowerPlotBESS = () => {
  const { projectId } = useParams()
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
    } else if (range === '7d') {
      start = end.subtract(7, 'days')
    } else if (range === 'yesterday') {
      start = dayjs().subtract(1, 'day').startOf('day')
      setIsAutoUpdating(false) // Disable auto-update for "yesterday" view
    } else {
      setIsAutoUpdating(true) // Enable auto-update for relative time ranges
    }

    setStartTime(start.toISOString())
    setEndTime(end.toISOString())
    setInterval(getInterval(start.toISOString(), end.toISOString()))
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

  const handleRelayout = (event: Readonly<PlotRelayoutEvent>) => {
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

  const project = useSelectProject(projectId!)
  const projectTimeZone = project.data?.time_zone ?? 'UTC'

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

  const data = useGetTimeSeries({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      sensor_type_name_shorts: [
        'meter_active_power',
        'project_soc_percent',
        'bess_pcs_available_charge_power',
        'bess_pcs_available_discharge_power',
      ],
      start: roundTime(startTime, interval, 'down'),
      end: roundTime(endTime, interval, 'up'),
      interval: interval,
    },
    queryOptions: {
      enabled: !!project.data && !!startTime && !!endTime,
      refetchOnWindowFocus: false,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every 60 seconds
      staleTime: QUERY_TIME.THIRTY_SECONDS, // Consider data stale after 30 seconds
    },
  })

  // Aggregate project-level available charge/discharge power from all PCS devices
  const timeSeriesData = data.data
  const projectDetails = project.data

  const aggregatedData = useMemo(() => {
    if (!timeSeriesData || !projectDetails) return timeSeriesData

    const chargeTraces = timeSeriesData.filter(
      (d) => d.sensor_type_name === 'bess_pcs_available_charge_power',
    )
    const dischargeTraces = timeSeriesData.filter(
      (d) => d.sensor_type_name === 'bess_pcs_available_discharge_power',
    )
    const otherTraces = timeSeriesData.filter(
      (d) =>
        d.sensor_type_name !== 'bess_pcs_available_charge_power' &&
        d.sensor_type_name !== 'bess_pcs_available_discharge_power',
    )

    const aggregated: typeof timeSeriesData = [...otherTraces]

    // Get current time to filter out future timestamps
    const now = dayjs()

    // Aggregate charge power: sum all PCS values, negate, clip to -poi
    if (chargeTraces.length > 0) {
      const poi = projectDetails.poi
      const firstTrace = chargeTraces[0]

      // Filter out future timestamps
      const filteredIndices = firstTrace.x
        .map((timestamp, idx) => ({
          timestamp,
          idx,
        }))
        .filter(
          ({ timestamp }) =>
            dayjs(timestamp).isBefore(now) || dayjs(timestamp).isSame(now),
        )
        .map(({ idx }) => idx)

      const filteredX = filteredIndices.map((idx) => firstTrace.x[idx])
      const aggregatedY = filteredIndices.map((idx) => {
        const values = chargeTraces.map((trace) => trace.y[idx])
        // If all values are null/undefined, return null to avoid showing zero
        if (values.every((v) => v === null || v === undefined)) {
          return null
        }
        const sum = values.reduce<number>((acc, v) => acc + (v || 0), 0)
        const mw = -sum
        return Math.max(mw, -poi)
      })

      // Only add trace if there's at least one non-null value
      if (aggregatedY.some((v) => v !== null)) {
        aggregated.push({
          ...firstTrace,
          x: filteredX,
          y: aggregatedY as number[], // Plotly supports null for gaps, cast to satisfy type
          name: 'Available Charge Power',
        })
      }
    }

    // Aggregate discharge power: sum all PCS values, clip to poi
    if (dischargeTraces.length > 0) {
      const poi = projectDetails.poi
      const firstTrace = dischargeTraces[0]

      // Filter out future timestamps
      const filteredIndices = firstTrace.x
        .map((timestamp, idx) => ({
          timestamp,
          idx,
        }))
        .filter(
          ({ timestamp }) =>
            dayjs(timestamp).isBefore(now) || dayjs(timestamp).isSame(now),
        )
        .map(({ idx }) => idx)

      const filteredX = filteredIndices.map((idx) => firstTrace.x[idx])
      const aggregatedY = filteredIndices.map((idx) => {
        const values = dischargeTraces.map((trace) => trace.y[idx])
        // If all values are null/undefined, return null to avoid showing zero
        if (values.every((v) => v === null || v === undefined)) {
          return null
        }
        const sum = values.reduce<number>((acc, v) => acc + (v || 0), 0)
        return Math.min(sum, poi)
      })

      // Only add trace if there's at least one non-null value
      if (aggregatedY.some((v) => v !== null)) {
        aggregated.push({
          ...firstTrace,
          x: filteredX,
          y: aggregatedY as number[], // Plotly supports null for gaps, cast to satisfy type
          name: 'Available Discharge Power',
        })
      }
    }

    return aggregated
  }, [projectDetails, timeSeriesData])

  return (
    <CustomCard
      title="Meter Power"
      style={{ flex: 2 }}
      headerChildren={
        <Group>
          <Tooltip label="Pan Left">
            <Button
              size="xs"
              variant="outline"
              onClick={() => handlePan('left')}
            >
              <IconArrowLeft />
            </Button>
          </Tooltip>
          <Button.Group>
            <Tooltip label="Reset to the last 24 hours. You can also zoom by scrolling.">
              <Button size="xs" variant="outline" onClick={handleDefaultView}>
                Last 24 Hours
              </Button>
            </Tooltip>
            <Menu>
              <Menu.Target>
                <Tooltip label="Select a time range">
                  <Button size="xs" variant="outline">
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
              variant="outline"
              onClick={() => handlePan('right')}
            >
              <IconArrowRight />
            </Button>
          </Tooltip>
        </Group>
      }
    >
      <PlotlyPlot
        data={aggregatedData?.map((d) => {
          const isAvailableCharge =
            d.sensor_type_name === 'bess_pcs_available_charge_power'
          const isAvailableDischarge =
            d.sensor_type_name === 'bess_pcs_available_discharge_power'
          const isSoc = d.sensor_type_name === 'project_soc_percent'

          return {
            x: d.x,
            y: d.y,
            name: d.name,
            fill:
              isSoc || isAvailableCharge || isAvailableDischarge
                ? null
                : 'tozeroy',
            line: {
              color: isSoc
                ? theme.colors.blue[7]
                : isAvailableCharge || isAvailableDischarge
                  ? theme.colors.orange[7]
                  : theme.colors.green[7],
              dash:
                isAvailableCharge || isAvailableDischarge ? 'dot' : undefined,
            },
            yaxis: isSoc ? 'y2' : 'y',
          }
        })}
        xAxisTimeZone={projectTimeZone}
        layout={
          project.data && {
            yaxis: {
              title: { text: 'Power (MW)' },
              fixedrange: true,
              range: [project.data.poi * 1.05 * -1, project.data.poi * 1.05],
            },
            yaxis2: {
              title: { text: 'SOC' },
              fixedrange: true,
              range: [0, 1.05],
              overlaying: 'y',
              side: 'right',
              tickformat: '.0%',
            },
            xaxis: {
              type: 'date',
              fixedrange: false,
              tickangle: 0,
            },
          }
        }
        onRelayout={handleRelayout}
        isLoading={data.isLoading}
        error={data.error}
        config={{ responsive: true, scrollZoom: true }}
      />
    </CustomCard>
  )
}

const CurrentTime = ({ timezone }: { timezone: string }) => {
  const [currentTime, setCurrentTime] = useState(() =>
    dayjs().tz(timezone).format('MMM D, YYYY HH:mm:ss'),
  )

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(dayjs().tz(timezone).format('MMM D, YYYY HH:mm:ss'))
    }, 1000)

    return () => clearInterval(interval)
  }, [timezone])

  return (
    <Text size="sm" style={{ fontFamily: 'monospace' }}>
      {currentTime}
    </Text>
  )
}

const KPICards = () => {
  const { projectId } = useParams()
  const { ref: containerRef, width: containerWidth } = useElementSize()
  const { ref: contentRef, width: contentWidth } = useElementSize()
  const [rotationOffset, setRotationOffset] = useState(0)
  const [isHovered, setIsHovered] = useState(false)
  const [queryDate, setQueryDate] = useState(dayjs().format('YYYY-MM-DD'))

  const project = useSelectProject(projectId!)
  const projectKPIInstances = useGetKPIInstances({
    queryParams: {
      project_ids: [projectId || '-1'],
      deep: true,
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const projectKPITypeIds = projectKPIInstances.data?.map(
    (kpiInstance) => kpiInstance.kpi_type_id,
  )

  const favoritedKPITypes = useGetUserFavoriteKPITypes({})

  const kpiTypeIds = favoritedKPITypes.data?.map(
    (kpiInstance) => kpiInstance.kpi_type_id,
  )

  const selectedKPITypeIds = (projectKPITypeIds || []).filter((id) =>
    (kpiTypeIds || []).includes(id),
  )

  const data = useGetKPISummaryCards({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      kpi_type_ids: selectedKPITypeIds,
      date: queryDate,
    },
    queryOptions: {
      enabled:
        !!projectId && !!favoritedKPITypes.data && !!projectKPIInstances.data,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every 60 seconds
      staleTime: QUERY_TIME.THIRTY_SECONDS, // Consider data stale after 30 seconds
    },
  })

  // Update queryDate when we detect today has no data (defer to avoid cascading renders)
  useEffect(() => {
    const today = dayjs().format('YYYY-MM-DD')
    if (
      data.isSuccess &&
      data.data &&
      data.data.length === 0 &&
      queryDate === today
    ) {
      // Defer state update to avoid cascading renders
      queueMicrotask(() => {
        setQueryDate(dayjs().subtract(1, 'day').format('YYYY-MM-DD'))
      })
    }
  }, [data.isSuccess, data.data, queryDate])

  const contentIsGreaterThanContainer = contentWidth > containerWidth

  const filteredData = data.data?.filter(
    (kpi) => kpi.value !== null && kpi.value !== undefined,
  )

  const items = filteredData?.map((kpi) => kpi)

  // Derive rotation offset: reset to 0 when content fits in container
  const effectiveRotationOffset = contentIsGreaterThanContainer
    ? rotationOffset
    : 0

  const rotatedItems = items
    ?.slice(effectiveRotationOffset)
    .concat(items?.slice(0, effectiveRotationOffset))

  // Rotate items every second when content is greater than container and not hovered
  useEffect(() => {
    if (!contentIsGreaterThanContainer || isHovered || !items?.length) return

    const interval = setInterval(() => {
      setRotationOffset((prev) => (prev + 1) % items.length)
    }, 4000)

    return () => {
      clearInterval(interval)
    }
  }, [contentIsGreaterThanContainer, items?.length, isHovered])

  // Reset rotation offset state when content is no longer greater than container
  useEffect(() => {
    if (!contentIsGreaterThanContainer && rotationOffset !== 0) {
      // Defer state update to avoid cascading renders
      queueMicrotask(() => {
        setRotationOffset(0)
      })
    }
  }, [contentIsGreaterThanContainer, rotationOffset])

  if (
    project.isLoading ||
    favoritedKPITypes.isLoading ||
    data.isLoading ||
    projectKPIInstances.isLoading
  ) {
    return (
      <Skeleton radius="md">
        <EmptyKPICard />
      </Skeleton>
    )
  }

  return (
    <Group
      ref={containerRef}
      style={{ overflow: 'hidden' }}
      w="100%"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Group wrap="nowrap" ref={contentRef}>
        {rotatedItems?.map((kpi) => (
          <KPICard
            key={kpi.kpi_type_id}
            {...kpi}
            link={`kpis/type/${kpi.kpi_type_id}`}
          />
        ))}
      </Group>
    </Group>
  )
}

function KioskMode({
  enabled,
  setEnabled,
}: {
  enabled: boolean
  setEnabled: (enabled: boolean) => void
}) {
  const INTERVAL = 60

  const { projectId } = useParams()
  const navigate = useNavigate()

  // Query data for all projects
  const projects = useGetProjects({
    queryParams: {
      deep: true,
    },
  })

  // Get an array of all project IDs
  const projectIds = useMemo(
    () => projects.data?.map((project) => project.project_id),
    [projects.data],
  )

  // Effect to handle kiosk mode
  useEffect(() => {
    // If kiosk mode is not enabled, do nothing
    if (!enabled) return

    // If there are no project IDs, do nothing
    if (!projectIds) return

    // Set an interval to rotate to the next project
    const interval = setInterval(() => {
      // Find the current project index in the array
      const currentIndex = projectIds.findIndex((id) => id === projectId)

      // Get the next project ID (wrap around to the beginning if at the end)
      const nextIndex =
        currentIndex === -1 || currentIndex === projectIds.length - 1
          ? 0
          : currentIndex + 1

      // Navigate to the next project
      const nextProjectId = projectIds[nextIndex]
      navigate(`/projects/${nextProjectId}`)
    }, INTERVAL * 1000)

    // Cleanup interval on component unmount
    return () => clearInterval(interval)
  }, [navigate, projectIds, enabled, projectId])

  return (
    <Tooltip
      label={`Kiosk Mode - When enabled, the page will automatically rotate to the next project every ${INTERVAL} seconds.`}
      refProp="rootRef"
    >
      <Switch
        size="md"
        onLabel={<IconRepeat size={16} />}
        offLabel={<IconRepeatOff size={16} />}
        checked={enabled}
        onChange={(event) => setEnabled(event.currentTarget.checked)}
      />
    </Tooltip>
  )
}

const BatteryHealth = () => {
  const { projectId } = useParams()
  const theme = useMantineTheme()
  const navigate = useNavigate()
  const [showCycleData, setShowCycleData] = useState(false)
  const [showSocData, setShowSocData] = useState(false)
  const [showRestSocData, setShowRestSocData] = useState(false)

  // Get project data to access COD
  const project = useSelectProject(projectId!)

  // Battery Health KPI IDs - using string KPIs instead of bank KPIs
  const batteryHealthKpiIds = [
    KPITypeEnum.BESS_STRING_SOH,
    KPITypeEnum.BESS_MODULE_SOH,
    KPITypeEnum.BESS_STRING_CYCLE_COUNT,
    KPITypeEnum.BESS_STRING_AVERAGE_SOC_PERCENT,
    KPITypeEnum.BESS_STRING_RESTING_SOC_PERCENT,
    KPITypeEnum.BESS_STRING_DEPTH_OF_DISCHARGE,
  ]

  const kpiData = useGetKPISummaryCards({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      kpi_type_ids: batteryHealthKpiIds,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every 60 seconds
      staleTime: QUERY_TIME.THIRTY_SECONDS, // Consider data stale after 30 seconds
    },
  })

  // Fetch daily KPI data for SOH chart
  const dailyKpiData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || '-1'],
      kpi_type_ids: [KPITypeEnum.BESS_STRING_SOH],
      start: project.data?.cod
        ? dayjs(project.data.cod).format('YYYY-MM-DD')
        : dayjs().subtract(2, 'years').format('YYYY-MM-DD'),
      end: dayjs().format('YYYY-MM-DD'),
      include_device_data: false,
      include_all_dates: false,
    },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every 60 seconds
      staleTime: QUERY_TIME.THIRTY_SECONDS, // Consider data stale after 30 seconds
    },
  })

  // Fetch daily cycle data for secondary axis
  const dailyCycleData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || '-1'],
      kpi_type_ids: [KPITypeEnum.BESS_STRING_CYCLE_COUNT],
      start: project.data?.cod
        ? dayjs(project.data.cod).format('YYYY-MM-DD')
        : dayjs().subtract(2, 'years').format('YYYY-MM-DD'),
      end: dayjs().format('YYYY-MM-DD'),
      include_device_data: false,
      include_all_dates: false,
    },
    queryOptions: {
      enabled: !!projectId && showCycleData,
    },
  })

  // Fetch daily SOC data for secondary axis
  const dailySocData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || '-1'],
      kpi_type_ids: [KPITypeEnum.BESS_STRING_AVERAGE_SOC_PERCENT],
      start: project.data?.cod
        ? dayjs(project.data.cod).format('YYYY-MM-DD')
        : dayjs().subtract(2, 'years').format('YYYY-MM-DD'),
      end: dayjs().format('YYYY-MM-DD'),
      include_device_data: false,
      include_all_dates: false,
    },
    queryOptions: {
      enabled: !!projectId && showSocData,
    },
  })

  // Fetch daily Rest SOC data for secondary axis
  const dailyRestSocData = useGetOperationalKPIData({
    queryParams: {
      project_ids: [projectId || '-1'],
      kpi_type_ids: [KPITypeEnum.BESS_STRING_RESTING_SOC_PERCENT],
      start: project.data?.cod
        ? dayjs(project.data.cod).format('YYYY-MM-DD')
        : dayjs().subtract(2, 'years').format('YYYY-MM-DD'),
      end: dayjs().format('YYYY-MM-DD'),
      include_device_data: false,
      include_all_dates: false,
    },
    queryOptions: {
      enabled: !!projectId && showRestSocData,
    },
  })

  // Extract specific KPI values
  const sohData = kpiData.data?.find(
    (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_SOH,
  )
  const cycleData = kpiData.data?.find(
    (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_CYCLE_COUNT,
  )
  const avgSocData = kpiData.data?.find(
    (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_AVERAGE_SOC_PERCENT,
  )
  const restSocData = kpiData.data?.find(
    (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_RESTING_SOC_PERCENT,
  )
  const avgDodData = kpiData.data?.find(
    (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_DEPTH_OF_DISCHARGE,
  )

  // Get the last available SOH value from daily data
  const getLastSohValue = () => {
    if (dailyKpiData.data && dailyKpiData.data.length > 0) {
      const sohKpiData = dailyKpiData.data.find(
        (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_SOH,
      )
      if (
        sohKpiData?.data?.project_data &&
        sohKpiData.data.project_data.length > 0
      ) {
        // Get the last non-null value and convert to percentage
        const lastValue = sohKpiData.data.project_data
          .filter((val): val is number => val !== null)
          .slice(-1)[0]
        return lastValue ? lastValue * 100 : null
      }
    }
    // Fallback to summary card data
    return sohData?.ytd_value || sohData?.value || 100
  }

  const currentSoh = getLastSohValue() || 100

  // Calculate expected SOH for current date
  const getExpectedSoh = () => {
    // Determine start date: use COD if available, otherwise use first available data date
    let startDate: dayjs.Dayjs
    if (project.data?.cod) {
      startDate = dayjs(project.data.cod)
    } else if (dailyKpiData.data && dailyKpiData.data.length > 0) {
      const sohKpiData = dailyKpiData.data.find(
        (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_SOH,
      )
      if (sohKpiData?.data?.dates && sohKpiData.data.dates.length > 0) {
        startDate = dayjs(sohKpiData.data.dates[0])
      } else {
        return 100
      }
    } else {
      return 100
    }

    const currentDate = dayjs()
    const daysSinceStart = currentDate.diff(startDate, 'days')

    // Daily degradation rate: 1% per year = 1/365 = 0.00274% per day
    const dailyDegradationRate = 1 / 365
    const expectedValue = Math.max(
      100 - daysSinceStart * dailyDegradationRate,
      80,
    )

    return expectedValue
  }

  // Calculate expected SOH for the last actual data point date
  const getExpectedSohForLastDataPoint = () => {
    if (dailyKpiData.data && dailyKpiData.data.length > 0) {
      const sohKpiData = dailyKpiData.data.find(
        (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_SOH,
      )
      if (sohKpiData?.data?.dates && sohKpiData.data.dates.length > 0) {
        const lastDate = sohKpiData.data.dates[sohKpiData.data.dates.length - 1]

        // Determine start date: use COD if available, otherwise use first available data date
        let startDate: dayjs.Dayjs
        if (project.data?.cod) {
          startDate = dayjs(project.data.cod)
        } else {
          startDate = dayjs(sohKpiData.data.dates[0])
        }

        const lastDataDate = dayjs(lastDate)
        const daysSinceStart = lastDataDate.diff(startDate, 'days')

        // Daily degradation rate: 1% per year = 1/365 = 0.00274% per day
        const dailyDegradationRate = 1 / 365
        const expectedValue = Math.max(
          100 - daysSinceStart * dailyDegradationRate,
          80,
        )

        return expectedValue
      }
    }

    // Fallback to current date calculation
    return getExpectedSoh()
  }

  const expectedSoh = getExpectedSohForLastDataPoint()
  const sohDifference = currentSoh - expectedSoh
  const sohDifferenceFormatted =
    sohDifference > 0
      ? `+${sohDifference.toFixed(2)}%`
      : `${sohDifference.toFixed(2)}%`
  const sohDifferenceText = sohDifference > 0 ? 'above' : 'below'

  // Create SOH degradation chart data and zoom range
  const { chartData: sohChartData, defaultZoomRange } = useMemo(() => {
    // Generate expected SOH data with proper dates (20 years from start date)
    const generateExpectedSohData = () => {
      // Determine start date: use COD if available, otherwise use first available data date
      let startDate: dayjs.Dayjs
      if (project.data?.cod) {
        startDate = dayjs(project.data.cod)
      } else if (dailyKpiData.data && dailyKpiData.data.length > 0) {
        const sohKpiData = dailyKpiData.data.find(
          (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_SOH,
        )
        if (sohKpiData?.data?.dates && sohKpiData.data.dates.length > 0) {
          startDate = dayjs(sohKpiData.data.dates[0])
        } else {
          return { x: [], y: [] }
        }
      } else {
        return { x: [], y: [] }
      }

      const totalDays = 7300 // 20 years

      // Generate dates from start date to 20 years out
      const dates = []
      const expectedSoh = []

      for (let i = 0; i <= totalDays; i++) {
        const currentDate = startDate.add(i, 'days')
        dates.push(currentDate.format('YYYY-MM-DD'))

        // Daily degradation rate: 1% per year = 1/365 = 0.00274% per day
        const dailyDegradationRate = 1 / 365
        const expectedValue = Math.max(100 - i * dailyDegradationRate, 80)
        expectedSoh.push(expectedValue)
      }

      return { x: dates, y: expectedSoh }
    }

    const expectedSohData = generateExpectedSohData()

    // Use real daily KPI data if available
    let actualSohData: { x: string[]; y: number[] } | null = null
    if (dailyKpiData.data && dailyKpiData.data.length > 0) {
      const sohKpiData = dailyKpiData.data.find(
        (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_SOH,
      )
      if (sohKpiData?.data?.dates && sohKpiData?.data?.project_data) {
        const dates = sohKpiData.data.dates.map((date) =>
          dayjs(date).format('YYYY-MM-DD'),
        )
        const values = sohKpiData.data.project_data
          .filter((val): val is number => val !== null)
          .map((val) => val * 100) // Convert from decimal to percentage
        actualSohData = { x: dates, y: values }
      }
    }

    // Calculate default zoom range based on actual data
    const getDefaultZoomRange = () => {
      if (actualSohData && actualSohData.x.length > 0) {
        // If we have actual data, zoom to show that data with some padding
        const startDate = actualSohData.x[0]
        const endDate = actualSohData.x[actualSohData.x.length - 1]

        // Add 30 days padding on each side
        const paddedStart = dayjs(startDate)
          .subtract(30, 'days')
          .format('YYYY-MM-DD')
        const paddedEnd = dayjs(endDate).add(30, 'days').format('YYYY-MM-DD')

        return [paddedStart, paddedEnd]
      }

      // If no actual data, show first 2 years from start date
      if (project.data?.cod) {
        const codDate = dayjs(project.data.cod)
        const twoYearsLater = codDate.add(2, 'years').format('YYYY-MM-DD')
        return [project.data.cod, twoYearsLater]
      } else if (dailyKpiData.data && dailyKpiData.data.length > 0) {
        const sohKpiData = dailyKpiData.data.find(
          (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_SOH,
        )
        if (sohKpiData?.data?.dates && sohKpiData.data.dates.length > 0) {
          const startDate = dayjs(sohKpiData.data.dates[0])
          const twoYearsLater = startDate.add(2, 'years').format('YYYY-MM-DD')
          return [startDate.format('YYYY-MM-DD'), twoYearsLater]
        }
      }

      return undefined
    }

    const defaultZoomRange = getDefaultZoomRange()

    const chartData: Data[] = [
      {
        x: expectedSohData.x,
        y: expectedSohData.y,
        name: 'Expected SOH',
        line: { color: theme.colors.gray[4], dash: 'dash', width: 2 },
        type: 'scatter',
        hovertemplate: '%{y:.2f}%<extra></extra>',
      } satisfies Data,
    ]

    if (actualSohData && actualSohData.x.length > 0) {
      chartData.push({
        x: actualSohData.x,
        y: actualSohData.y,
        name: 'Actual SOH',
        line: { color: theme.colors.blue[6], width: 3 },
        type: 'scatter',
        hovertemplate: '%{y:.2f}%<extra></extra>',
      } satisfies Data)
    }

    // Add cycle data if enabled
    if (
      showCycleData &&
      dailyCycleData.data &&
      dailyCycleData.data.length > 0
    ) {
      const cycleKpiData = dailyCycleData.data.find(
        (kpi) => kpi.kpi_type_id === KPITypeEnum.BESS_STRING_CYCLE_COUNT,
      )
      if (cycleKpiData?.data?.dates && cycleKpiData?.data?.project_data) {
        const dates = cycleKpiData.data.dates.map((date) =>
          dayjs(date).format('YYYY-MM-DD'),
        )
        const values = cycleKpiData.data.project_data.filter(
          (val): val is number => val !== null,
        )
        chartData.push({
          x: dates,
          y: values,
          name: 'Cycle Count',
          type: 'bar',
          yaxis: 'y2',
          hovertemplate: '%{y:.0f}<extra></extra>',
          marker: { color: theme.colors.gray[6] },
        } satisfies Data)
      }
    }

    // Add SOC data if enabled
    if (showSocData && dailySocData.data && dailySocData.data.length > 0) {
      const socKpiData = dailySocData.data.find(
        (kpi) =>
          kpi.kpi_type_id === KPITypeEnum.BESS_STRING_AVERAGE_SOC_PERCENT,
      )
      if (socKpiData?.data?.dates && socKpiData?.data?.project_data) {
        const dates = socKpiData.data.dates.map((date) =>
          dayjs(date).format('YYYY-MM-DD'),
        )
        const values = socKpiData.data.project_data
          .filter((val): val is number => val !== null)
          .map((val) => val * 100) // Convert to percentage
        chartData.push({
          x: dates,
          y: values,
          name: 'String SOC',
          line: { color: theme.colors.green[6] },
          type: 'scatter',
          yaxis: 'y2',
          hovertemplate: '%{y:.1f}%<extra></extra>',
        } satisfies Data)
      }
    }

    // Add Rest SOC data if enabled
    if (
      showRestSocData &&
      dailyRestSocData.data &&
      dailyRestSocData.data.length > 0
    ) {
      const restSocKpiData = dailyRestSocData.data.find(
        (kpi) =>
          kpi.kpi_type_id === KPITypeEnum.BESS_STRING_RESTING_SOC_PERCENT,
      )
      if (restSocKpiData?.data?.dates && restSocKpiData?.data?.project_data) {
        const dates = restSocKpiData.data.dates.map((date) =>
          dayjs(date).format('YYYY-MM-DD'),
        )
        const values = restSocKpiData.data.project_data
          .filter((val): val is number => val !== null)
          .map((val) => val * 100) // Convert to percentage
        chartData.push({
          x: dates,
          y: values,
          name: 'String Rest SOC',
          line: { color: theme.colors.violet[6] },
          type: 'scatter',
          yaxis: 'y2',
          hovertemplate: '%{y:.1f}%<extra></extra>',
        } satisfies Data)
      }
    }

    return { chartData, defaultZoomRange }
  }, [
    theme,
    dailyKpiData.data,
    project.data,
    showCycleData,
    dailyCycleData.data,
    showSocData,
    dailySocData.data,
    showRestSocData,
    dailyRestSocData.data,
  ])

  // Show loading state
  if (kpiData.isLoading) {
    return (
      <CustomCard
        title={
          <Link
            to={`/projects/${projectId}/battery-health`}
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            Battery Health
          </Link>
        }
        style={{ height: 350, minHeight: 350 }}
      >
        <LoadingOverlay visible={true} />
      </CustomCard>
    )
  }

  const formatValue = (value: number | null | undefined, unit: string = '') => {
    if (value === null || value === undefined) return 'N/A'
    return `${value.toFixed(2)}${unit}`
  }

  // Calculate annual cycle count projection
  const calculateAnnualCycles = (ytdValue: number | null | undefined) => {
    if (!ytdValue) return null
    const currentDate = new Date()
    const startOfYear = new Date(currentDate.getFullYear(), 0, 1)
    const daysElapsed =
      (currentDate.getTime() - startOfYear.getTime()) / (1000 * 60 * 60 * 24)
    const daysInYear = 365
    return Math.round((ytdValue / daysElapsed) * daysInYear)
  }

  const getSohColor = (soh: number) => {
    if (soh >= 90) return theme.colors.green[6]
    if (soh >= 80) return theme.colors.yellow[6]
    return theme.colors.red[6]
  }

  // Check if we have any battery health data
  const hasBatteryData = sohData || cycleData || avgSocData

  if (!hasBatteryData) {
    return (
      <CustomCard
        title={
          <Link
            to={`/projects/${projectId}/battery-health`}
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            Battery Health
          </Link>
        }
        style={{ height: 350, minHeight: 350 }}
      >
        <Center h={200}>
          <Text c="dimmed">No battery health data available</Text>
        </Center>
      </CustomCard>
    )
  }

  return (
    <CustomCard
      title={
        <Link
          to={`/projects/${projectId}/battery-health`}
          style={{ textDecoration: 'none', color: 'inherit' }}
        >
          Battery Health
        </Link>
      }
      allowFullscreen={false}
      style={{ height: 350, minHeight: 350 }}
    >
      <Stack gap="md">
        {/* SOH Degradation Chart */}
        {sohData && (
          <Box>
            <Center>
              <Box w="100%">
                <PlotlyPlot
                  data={sohChartData}
                  layout={{
                    height: 200,
                    margin: { l: 40, r: 100, t: 20, b: 20 },
                    dragmode: 'zoom',
                    xaxis: {
                      type: 'date',
                      showgrid: true,
                      gridcolor: theme.colors.gray[2],
                      rangeslider: { visible: false },
                      range: defaultZoomRange,
                      fixedrange: false,
                    },
                    yaxis: {
                      title: { text: 'SOH (%)' },
                      range: [80, 100],
                      showgrid: true,
                      gridcolor: theme.colors.gray[2],
                      tickformat: '.2f',
                      fixedrange: true,
                    },
                    yaxis2:
                      showCycleData || showSocData || showRestSocData
                        ? {
                            title: {
                              text: showCycleData
                                ? 'Cycle Count'
                                : showSocData
                                  ? 'String SOC (%)'
                                  : 'String Rest SOC (%)',
                              font: {
                                color: showCycleData
                                  ? theme.colors.gray[6]
                                  : showSocData
                                    ? theme.colors.green[6]
                                    : theme.colors.violet[6],
                              },
                            },
                            overlaying: 'y',
                            side: 'right',
                            showgrid: false,
                            range: showCycleData ? [0, 2] : [0, 100],
                            tickformat: showCycleData ? '.1f' : '.1f',
                            fixedrange: true,
                            tickfont: {
                              color: showCycleData
                                ? theme.colors.gray[6]
                                : showSocData
                                  ? theme.colors.green[6]
                                  : theme.colors.violet[6],
                            },
                          }
                        : undefined,
                    showlegend: false,
                    plot_bgcolor: 'transparent',
                    paper_bgcolor: 'transparent',
                  }}
                  config={{
                    scrollZoom: true,
                    displayModeBar: false,
                  }}
                  isLoading={kpiData.isLoading}
                  error={kpiData.error}
                />
              </Box>
            </Center>

            {/* Custom Legend Overlay */}
            <Group justify="center" gap="lg" mt={-10} mb={10}>
              <Group gap="xs" align="center">
                <Box
                  w={16}
                  h={2}
                  style={{
                    backgroundColor: theme.colors.gray[4],
                    borderTop: `2px dashed ${theme.colors.gray[4]}`,
                  }}
                />
                <Text size="xs" c="dimmed">
                  Expected SOH
                </Text>
              </Group>
              <Group gap="xs" align="center">
                <Box
                  w={16}
                  h={2}
                  style={{
                    backgroundColor: theme.colors.blue[6],
                  }}
                />
                <Text size="xs" c="dimmed">
                  Actual SOH
                </Text>
              </Group>
            </Group>
          </Box>
        )}

        {/* Key Metrics Grid */}
        <Grid>
          {/* SOH Metrics */}
          <Grid.Col span={4}>
            <Stack align="center" gap="xs">
              {sohData ? (
                <>
                  <Box ta="center">
                    <Text
                      size="xl"
                      fw={700}
                      c={getSohColor(currentSoh)}
                      style={{ cursor: 'pointer' }}
                      onClick={() =>
                        navigate(
                          `/projects/${projectId}/kpis/type/${KPITypeEnum.BESS_STRING_SOH}`,
                        )
                      }
                      onMouseEnter={() => {
                        setShowCycleData(false)
                        setShowSocData(false)
                        setShowRestSocData(false)
                      }}
                    >
                      {formatValue(currentSoh, '%')}
                    </Text>
                    <Tooltip label={sohData.info || ''} withArrow>
                      <Text
                        size="xs"
                        c="dimmed"
                        style={{ cursor: 'pointer' }}
                        onClick={() =>
                          navigate(
                            `/projects/${projectId}/kpis/type/${KPITypeEnum.BESS_STRING_SOH}`,
                          )
                        }
                        onMouseEnter={() => {
                          setShowCycleData(false)
                          setShowSocData(false)
                          setShowRestSocData(false)
                        }}
                      >
                        {sohData.title}
                      </Text>
                    </Tooltip>
                    <Text size="xs" c="dimmed">
                      {sohDifferenceFormatted} {sohDifferenceText} expected
                    </Text>
                  </Box>
                </>
              ) : (
                <Box ta="center">
                  <Text size="lg" c="dimmed">
                    N/A
                  </Text>
                  <Text
                    size="xs"
                    c="dimmed"
                    style={{ cursor: 'pointer' }}
                    onClick={() =>
                      navigate(
                        `/projects/${projectId}/kpis/type/${KPITypeEnum.BESS_STRING_SOH}`,
                      )
                    }
                  >
                    System SOH
                  </Text>
                </Box>
              )}
            </Stack>
          </Grid.Col>

          {/* Cycles YTD */}
          <Grid.Col span={4}>
            <Stack align="center" gap="xs">
              <Box ta="center">
                <Text
                  size="xl"
                  fw={700}
                  c={theme.colors.gray[6]}
                  style={{ cursor: 'pointer' }}
                  onClick={() =>
                    navigate(
                      `/projects/${projectId}/kpis/type/${KPITypeEnum.BESS_STRING_CYCLE_COUNT}`,
                    )
                  }
                  onMouseEnter={() => {
                    setShowCycleData(true)
                    setShowSocData(false)
                    setShowRestSocData(false)
                  }}
                >
                  {formatValue(cycleData?.ytd_value || cycleData?.value, '')}
                </Text>
                <Tooltip label={cycleData?.info || ''} withArrow>
                  <Text
                    size="xs"
                    c="dimmed"
                    style={{ cursor: 'pointer' }}
                    onClick={() =>
                      navigate(
                        `/projects/${projectId}/kpis/type/${KPITypeEnum.BESS_STRING_CYCLE_COUNT}`,
                      )
                    }
                    onMouseEnter={() => {
                      setShowCycleData(true)
                      setShowSocData(false)
                      setShowRestSocData(false)
                    }}
                  >
                    {cycleData?.title || 'Cycles YTD'}
                  </Text>
                </Tooltip>
                {cycleData && calculateAnnualCycles(cycleData.ytd_value) && (
                  <Text size="xs" c="dimmed">
                    Projected: {calculateAnnualCycles(cycleData.ytd_value)}/year
                  </Text>
                )}
              </Box>
              {avgDodData && (
                <Badge
                  variant="light"
                  color="gray"
                  size="sm"
                  style={{ cursor: 'pointer' }}
                  onClick={() =>
                    navigate(
                      `/projects/${projectId}/kpis/type/${KPITypeEnum.BESS_STRING_DEPTH_OF_DISCHARGE}`,
                    )
                  }
                >
                  <IconActivity size={12} style={{ marginRight: 4 }} />
                  {formatValue(
                    avgDodData.ytd_value || avgDodData.value,
                    '%',
                  )}{' '}
                  Avg DOD
                </Badge>
              )}
            </Stack>
          </Grid.Col>

          {/* SOC Metrics */}
          <Grid.Col span={4}>
            <Stack align="center" gap="xs">
              <Box ta="center">
                <Text
                  size="lg"
                  fw={700}
                  c={theme.colors.green[6]}
                  style={{ cursor: 'pointer' }}
                  onClick={() =>
                    navigate(
                      `/projects/${projectId}/kpis/type/${KPITypeEnum.BESS_STRING_AVERAGE_SOC_PERCENT}`,
                    )
                  }
                  onMouseEnter={() => {
                    setShowSocData(true)
                    setShowCycleData(false)
                    setShowRestSocData(false)
                  }}
                >
                  {formatValue(avgSocData?.ytd_value || avgSocData?.value, '%')}
                </Text>
                <Tooltip label={avgSocData?.info || ''} withArrow>
                  <Text
                    size="xs"
                    c="dimmed"
                    style={{ cursor: 'pointer' }}
                    onClick={() =>
                      navigate(
                        `/projects/${projectId}/kpis/type/${KPITypeEnum.BESS_STRING_AVERAGE_SOC_PERCENT}`,
                      )
                    }
                    onMouseEnter={() => {
                      setShowSocData(true)
                      setShowCycleData(false)
                      setShowRestSocData(false)
                    }}
                  >
                    String SOC YTD
                  </Text>
                </Tooltip>
              </Box>
              {restSocData && (
                <Box ta="center">
                  <Text
                    size="sm"
                    fw={500}
                    c={theme.colors.gray[6]}
                    style={{ cursor: 'pointer' }}
                    onClick={() =>
                      navigate(
                        `/projects/${projectId}/kpis/type/${KPITypeEnum.BESS_STRING_RESTING_SOC_PERCENT}`,
                      )
                    }
                    onMouseEnter={() => {
                      setShowRestSocData(true)
                      setShowCycleData(false)
                      setShowSocData(false)
                    }}
                  >
                    {formatValue(
                      restSocData.ytd_value || restSocData.value,
                      '%',
                    )}
                  </Text>
                  <Tooltip label={restSocData.info || ''} withArrow>
                    <Text
                      size="xs"
                      c="dimmed"
                      style={{ cursor: 'pointer' }}
                      onClick={() =>
                        navigate(
                          `/projects/${projectId}/kpis/type/${KPITypeEnum.BESS_STRING_RESTING_SOC_PERCENT}`,
                        )
                      }
                      onMouseEnter={() => {
                        setShowRestSocData(true)
                        setShowCycleData(false)
                        setShowSocData(false)
                      }}
                    >
                      String Rest SOC YTD
                    </Text>
                  </Tooltip>
                </Box>
              )}
            </Stack>
          </Grid.Col>
        </Grid>
      </Stack>
    </CustomCard>
  )
}

const ContractualKPIOverview = ({
  project,
  onExpandedChange,
}: {
  project: Project | null | undefined
  onExpandedChange?: (expanded: boolean) => void
}) => {
  const { projectId } = useParams()
  const theme = useMantineTheme()
  const navigate = useNavigate()
  const [contractModalOpen, setContractModalOpen] = useState(false)
  const [selectedContractUrl, setSelectedContractUrl] = useState<string | null>(
    null,
  )

  // Size values based on project type - BESS projects get larger sizes
  const isBESSProject =
    project?.project_type_id === ProjectTypeEnum.BESS ||
    project?.project_type_id === ProjectTypeEnum.PVS
  const expandedFlex = isBESSProject ? 0.5 : 0.3
  const expandedMinHeight = isBESSProject ? 180 : 80
  const expandedMaxHeight = isBESSProject ? 250 : 150

  // Initialize expanded state from localStorage, default to true (expanded)
  const [isExpanded, setIsExpanded] = useState(() => {
    const saved = localStorage.getItem(`contractRisksExpanded_${projectId}`)
    return saved !== null ? JSON.parse(saved) : true
  })

  // Update expanded state when projectId changes
  useEffect(() => {
    const saved = localStorage.getItem(`contractRisksExpanded_${projectId}`)
    queueMicrotask(() =>
      setIsExpanded(saved !== null ? JSON.parse(saved) : true),
    )
  }, [projectId])

  // Save expanded state to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(
      `contractRisksExpanded_${projectId}`,
      JSON.stringify(isExpanded),
    )
    // Notify parent component of the change
    onExpandedChange?.(isExpanded)
  }, [isExpanded, onExpandedChange, projectId])

  // Get contract KPI data with thresholds first (lightweight query)
  const contractKPIData = useGetContractKPIs({
    pathParams: { projectId: projectId || '-1' },
    queryOptions: {
      enabled: !!projectId,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every 60 seconds
      staleTime: QUERY_TIME.THIRTY_SECONDS, // Consider data stale after 30 seconds
    },
  })

  // Extract contractual KPI type IDs from contract data
  const contractualKpiTypeIds = useMemo(() => {
    if (!contractKPIData.data) return []
    return contractKPIData.data.map((ck) => ck.kpi_type_id)
  }, [contractKPIData.data])

  // Only fetch KPI summary cards for contractual KPIs (not all KPIs)
  const kpiData = useGetKPISummaryCards({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      kpi_type_ids:
        contractualKpiTypeIds.length > 0 ? contractualKpiTypeIds : undefined,
    },
    queryOptions: {
      enabled: !!projectId && contractualKpiTypeIds.length > 0,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every 60 seconds
      staleTime: QUERY_TIME.THIRTY_SECONDS, // Consider data stale after 30 seconds
    },
  })

  // All fetched KPIs are contractual (no need to filter)
  const contractualKPIs = kpiData.data || []

  // Create a map of KPI type ID to contract KPI data for easy lookup
  const contractKPIMap = useMemo(() => {
    if (!contractKPIData.data) return new Map()
    return new Map(contractKPIData.data.map((ck) => [ck.kpi_type_id, ck]))
  }, [contractKPIData.data])

  // Function to get threshold value for current date
  const getCurrentThreshold = (kpiTypeId: number) => {
    const contractKPI = contractKPIMap.get(kpiTypeId)
    if (!contractKPI?.threshold?.values) return null

    return getKPIThresholdbyDate(contractKPI.threshold, new Date(), 'discrete')
  }

  // Function to determine status color based on value vs threshold
  const getStatusColor = (
    value: number | null | undefined,
    threshold: number | null | undefined,
    unit?: string | null,
  ) => {
    if (
      value === null ||
      value === undefined ||
      threshold === null ||
      threshold === undefined
    ) {
      return theme.colors.gray[4] // Gray for no data
    }

    // For percentage KPIs, convert threshold to match the value format
    const normalizedThreshold = unit === '%' ? threshold * 100 : threshold

    // For KPIs where higher is better (most cases)
    const percentage = (value / normalizedThreshold) * 100

    if (percentage >= 100) {
      return theme.colors.green[6] // Green - above threshold
    } else if (percentage >= 90) {
      return theme.colors.orange[6] // Orange - close to threshold
    } else {
      return theme.colors.red[6] // Red - below threshold
    }
  }

  // Function to format value with unit
  const formatValue = (
    value: number | null | undefined,
    unit?: string | null,
    isThreshold: boolean = false,
  ) => {
    if (value === null || value === undefined) return 'N/A'

    // For percentage thresholds, multiply by 100 to match the displayed data
    const displayValue = unit === '%' && isThreshold ? value * 100 : value

    const formatted = displayValue.toFixed(2)
    return unit ? `${formatted} ${unit}` : formatted
  }

  // Show loading state
  if (kpiData.isLoading || contractKPIData.isLoading) {
    return (
      <CustomCard title="Contract Risks">
        <LoadingOverlay visible={true} />
      </CustomCard>
    )
  }

  // Show placeholder if no contractual KPIs
  if (contractualKPIs.length === 0) {
    // Create placeholder KPIs for demonstration
    const placeholderKPIs = [
      {
        kpi_type_id: 0,
        contract_id: null,
        link: '',
        is_visible: true,
        ytd_value: 97.2,
        title: 'Project Availability',
        info: 'Example contractual KPI',
        value: null,
        prefix: '',
        suffix: '',
        unit: '%',
        change: null,
        icon: null,
        valColor: undefined,
        aggregation_method: undefined,
        threshold: 95.0,
        counterparty: 'Utility Company A',
      },
      {
        kpi_type_id: 1,
        contract_id: null,
        link: '',
        is_visible: true,
        ytd_value: 102.3,
        title: 'Energy Production',
        info: 'Example contractual KPI',
        value: null,
        prefix: '',
        suffix: '',
        unit: 'MWh',
        change: null,
        icon: null,
        valColor: undefined,
        aggregation_method: undefined,
        threshold: 100.0,
        counterparty: 'Utility Company A',
      },
    ]

    return (
      <CustomCard
        title="Contract Risks"
        headerChildren={
          <Group justify="space-between" align="center">
            <Tooltip label="Add new contractual KPI">
              <Button
                variant="light"
                size="sm"
                onClick={() =>
                  navigate(`/projects/${projectId}/kpis?openRequestModal=true`)
                }
              >
                Add New
              </Button>
            </Tooltip>
            <Tooltip label={isExpanded ? 'Collapse' : 'Expand'}>
              <ActionIcon
                variant="subtle"
                onClick={() => setIsExpanded(!isExpanded)}
              >
                {isExpanded ? (
                  <IconChevronDown size={iconSize} stroke={iconStroke} />
                ) : (
                  <IconChevronUp size={iconSize} stroke={iconStroke} />
                )}
              </ActionIcon>
            </Tooltip>
          </Group>
        }
        style={{
          flex: isExpanded ? expandedFlex : '0 0 auto',
          minHeight: isExpanded ? expandedMinHeight : undefined,
        }}
        hideBody={!isExpanded}
      >
        {isExpanded && (
          <>
            <ScrollArea h="100%">
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>KPI</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>
                      Counterparty
                    </Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>
                      YTD Value
                    </Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>
                      Threshold
                    </Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>Status</Table.Th>
                    <Table.Th style={{ textAlign: 'center' }}>
                      Contract
                    </Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {placeholderKPIs.map((kpi, index) => {
                    const statusColor =
                      kpi.ytd_value >= kpi.threshold
                        ? theme.colors.green[6]
                        : theme.colors.red[6]

                    return (
                      <Table.Tr key={index} style={{ opacity: 0.6 }}>
                        <Table.Td>
                          <Text fw={500} c="dimmed">
                            {kpi.title}
                          </Text>
                          <Text size="xs" c="dimmed">
                            Example placeholder
                          </Text>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Text size="sm" c="dimmed">
                            {kpi.counterparty}
                          </Text>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Text c="dimmed">
                            {kpi.ytd_value} {kpi.unit}
                          </Text>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Text c="dimmed">
                            {kpi.threshold} {kpi.unit}
                          </Text>
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Box
                            w={12}
                            h={12}
                            style={{
                              backgroundColor: statusColor,
                              borderRadius: '50%',
                              display: 'inline-block',
                            }}
                          />
                        </Table.Td>
                        <Table.Td style={{ textAlign: 'center' }}>
                          <Button variant="light" size="xs" disabled c="dimmed">
                            View
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    )
                  })}
                </Table.Tbody>
              </Table>
            </ScrollArea>
            <Text size="sm" c="dimmed" ta="center" mt="md">
              Click Add New to request a KPI to be added
            </Text>
          </>
        )}
      </CustomCard>
    )
  }

  return (
    <CustomCard
      title="Contract Risks"
      headerChildren={
        <Group justify="space-between" align="center">
          <Tooltip label="Add new contractual KPI">
            <Button
              variant="light"
              size="sm"
              onClick={() =>
                navigate(`/projects/${projectId}/kpis?openRequestModal=true`)
              }
            >
              Add New
            </Button>
          </Tooltip>
          <Tooltip label={isExpanded ? 'Collapse' : 'Expand'}>
            <ActionIcon
              variant="subtle"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <IconChevronUp size={iconSize} stroke={iconStroke} />
              ) : (
                <IconChevronDown size={iconSize} stroke={iconStroke} />
              )}
            </ActionIcon>
          </Tooltip>
        </Group>
      }
      style={{
        flex: isExpanded ? expandedFlex : 0.1,
        minHeight: isExpanded ? expandedMinHeight : undefined,
      }}
      bodyStyle={{ maxHeight: expandedMaxHeight, overflowY: 'auto' }}
    >
      {isExpanded && (
        <>
          <ScrollArea h="100%">
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>KPI</Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>
                    Counterparty
                  </Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>YTD Value</Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>Threshold</Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>Status</Table.Th>
                  <Table.Th style={{ textAlign: 'center' }}>Contract</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {contractualKPIs.map((kpi) => {
                  const threshold = getCurrentThreshold(kpi.kpi_type_id)
                  const statusColor = getStatusColor(
                    kpi.ytd_value,
                    threshold,
                    kpi.unit,
                  )

                  // Get counterparty information from contract KPI data
                  const contractKPI = contractKPIMap.get(kpi.kpi_type_id)
                  const counterparty = contractKPI?.counter_company || 'N/A'

                  return (
                    <Table.Tr
                      key={kpi.kpi_type_id}
                      style={{ cursor: 'pointer' }}
                      onClick={() =>
                        navigate(
                          `/projects/${projectId}/kpis/contractual/${kpi.link}`,
                        )
                      }
                    >
                      <Table.Td>
                        <Text fw={500}>{kpi.title}</Text>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        <Text size="sm">{counterparty}</Text>
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        {formatValue(kpi.ytd_value, kpi.unit)}
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        {formatValue(threshold, kpi.unit, true)}
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        <Box
                          w={12}
                          h={12}
                          style={{
                            backgroundColor: statusColor,
                            borderRadius: '50%',
                            display: 'inline-block',
                          }}
                        />
                      </Table.Td>
                      <Table.Td style={{ textAlign: 'center' }}>
                        <Button
                          variant="light"
                          size="xs"
                          onClick={(e) => {
                            e.stopPropagation()
                            if (
                              contractKPI?.document_url?.startsWith('https://')
                            ) {
                              setSelectedContractUrl(contractKPI.document_url)
                              setContractModalOpen(true)
                            }
                          }}
                          disabled={
                            !contractKPI?.document_url?.startsWith('https://')
                          }
                        >
                          View
                        </Button>
                      </Table.Td>
                    </Table.Tr>
                  )
                })}
              </Table.Tbody>
            </Table>
          </ScrollArea>

          {/* Contract Document Modal */}
          <Modal
            opened={contractModalOpen}
            onClose={() => setContractModalOpen(false)}
            size="90%"
            title="Contract Document"
            styles={{
              title: { fontSize: '1.2rem', fontWeight: 600 },
            }}
          >
            {selectedContractUrl?.startsWith('https://') && (
              <iframe
                src={selectedContractUrl}
                sandbox="allow-popups"
                style={{
                  width: '100%',
                  height: '80vh',
                  border: 'none',
                  borderRadius: '4px',
                }}
                title="Contract Document"
              />
            )}
          </Modal>
        </>
      )}
    </CustomCard>
  )
}

type ViewMode = 'markets' | 'kpis' | 'devices'

const VIEW_MODE_STORAGE_KEY = 'bessHomeViewMode'

function getStoredViewMode(projectId: string): ViewMode | null {
  try {
    const raw = localStorage.getItem(`${VIEW_MODE_STORAGE_KEY}_${projectId}`)
    if (raw === 'markets' || raw === 'kpis' || raw === 'devices') {
      return raw
    }
  } catch {
    // ignore
  }
  return null
}

function storeViewMode(projectId: string, mode: ViewMode) {
  try {
    localStorage.setItem(`${VIEW_MODE_STORAGE_KEY}_${projectId}`, mode)
  } catch {
    // ignore
  }
}

const BESSProjectHome = () => {
  const { projectId } = useParams()
  const { ref: stackRef } = useElementSize()
  const [projectInfoModalOpen, setProjectInfoModalOpen] = useState(false)

  const project = useSelectProject(projectId!)
  const [kioskModeEnabled, setKioskModeEnabled] = useState(false)

  // Check QSE market access — fires in parallel with project query
  const qseAccess = useGetQSEAccess({
    pathParams: { projectId: projectId! },
    queryOptions: { enabled: !!projectId },
  })
  const hasQSEAccess = qseAccess.data?.has_access === true

  // Resolve the initial view mode once, after QSE settles
  const resolvedInitial = useMemo((): ViewMode => {
    const stored = getStoredViewMode(projectId!)
    if (stored) {
      // If stored is 'markets' but no access, fall back
      if (stored === 'markets' && !hasQSEAccess) return 'kpis'
      return stored
    }
    return hasQSEAccess ? 'markets' : 'kpis'
  }, [projectId, hasQSEAccess])

  const [viewMode, setViewMode] = useState<ViewMode>(resolvedInitial)

  // Keep viewMode in sync when the resolved default changes
  // (e.g. projectId navigation or QSE data arriving)
  useEffect(() => {
    queueMicrotask(() => setViewMode(resolvedInitial))
  }, [resolvedInitial])

  const handleViewModeChange = (value: string) => {
    const mode = value as ViewMode
    setViewMode(mode)
    storeViewMode(projectId!, mode)
  }

  const segmentedData = useMemo(() => {
    const items: { label: string; value: string }[] = []
    if (hasQSEAccess) {
      items.push({
        label: 'Markets',
        value: 'markets',
      })
    }
    items.push({ label: 'KPIs', value: 'kpis' })
    items.push({ label: 'System', value: 'devices' })
    return items
  }, [hasQSEAccess])

  if (project.isLoading) return <PageLoader />
  if (project.isError) return <PageError error={project.error} />
  if (project.data === undefined) return <PageError error={undefined} />

  const qseSettled = !qseAccess.isLoading

  return (
    <Stack p="md" h="100%" ref={stackRef}>
      <Group align="start">
        <Group gap="xs" flex={1}>
          <Title order={1} lh={1}>
            {project.data?.name_long}
          </Title>
          <Title order={1} fw="normal" lh={1}>
            {projectDescription(project.data)}
          </Title>
          <ActionIcon
            variant="subtle"
            size="sm"
            onClick={() => setProjectInfoModalOpen(true)}
            title="Project Information"
          >
            <IconInfoCircle size={16} />
          </ActionIcon>
        </Group>
        <Group gap="xs">
          <ProjectLabels projectId={projectId!} />
          <WeatherCard />
          <Card p={5} withBorder>
            <CurrentTime timezone={project.data?.time_zone} />
          </Card>
          <KioskMode
            enabled={kioskModeEnabled}
            setEnabled={setKioskModeEnabled}
          />
          {qseSettled && (
            <SegmentedControl
              size="xs"
              value={viewMode}
              onChange={handleViewModeChange}
              data={segmentedData}
            />
          )}
        </Group>
      </Group>

      <Box style={{ minHeight: 'fit-content', flexShrink: 0 }}>
        {!qseSettled ? (
          <Skeleton height={42} radius="md" />
        ) : viewMode === 'markets' && hasQSEAccess ? (
          <MarketStatsGrid projectId={projectId!} />
        ) : viewMode === 'kpis' ? (
          <KPICards />
        ) : (
          <DeviceTypeOverview />
        )}
      </Box>
      <Group flex={1} align="start">
        <Stack h="100%" flex={1}>
          {/* Performance Map + Battery Health (BESS only) */}
          <>
            <CustomCard
              title="Performance Map"
              info={
                <Stack gap="xs">
                  <Text fw={600}>Understanding Performance Values</Text>
                  <Text size="sm">
                    <Text component="span" fw={500}>
                      Data is realtime
                    </Text>{' '}
                    and updated every 30 seconds. This map displays BESS
                    (Battery Energy Storage System) performance metrics.
                  </Text>
                  <Text size="sm" fw={500}>
                    PCS (Power Conversion System) - Left Color Scale:
                  </Text>
                  <List spacing={4} withPadding>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500} c="green.7">
                          Bright Green:
                        </Text>{' '}
                        Higher power output from PCS
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500} c="gray.7">
                          Gray:
                        </Text>{' '}
                        Low/idle power output
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500}>
                          Glow:
                        </Text>{' '}
                        Charging shows a subtle white inner glow; discharging
                        shows a green outline glow. Glow intensity scales with
                        power magnitude.
                      </Text>
                    </List.Item>
                  </List>
                  <Text size="sm" fw={500}>
                    SOC (State of Charge) - Right Color Scale:
                  </Text>
                  <List spacing={4} withPadding>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500} c="green.7">
                          Green:
                        </Text>{' '}
                        High SOC (75-100%) - Battery is well charged
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500} c="yellow.7">
                          Yellow:
                        </Text>{' '}
                        Medium SOC (50-75%) - Moderate charge level
                      </Text>
                    </List.Item>
                    <List.Item>
                      <Text size="sm">
                        <Text component="span" fw={500} c="red.7">
                          Red:
                        </Text>{' '}
                        Low SOC (0-50%) - Battery charge is low
                      </Text>
                    </List.Item>
                  </List>
                  <Text size="sm" fw={500}>
                    Device Types:
                  </Text>
                  <Text size="sm">
                    •{' '}
                    <Text component="span" fw={500}>
                      PCS:
                    </Text>{' '}
                    Shows normalized AC power (-1 = full charge, 0 = idle, 1 =
                    full discharge)
                  </Text>
                  <Text size="sm">
                    •{' '}
                    <Text component="span" fw={500}>
                      DC Enclosures:
                    </Text>{' '}
                    Shows SOC percentage (0-100%)
                  </Text>
                  <Text size="sm">
                    •{' '}
                    <Text component="span" fw={500}>
                      BESS Strings:
                    </Text>{' '}
                    Shows SOC percentage (0-100%)
                  </Text>
                  <Text size="sm" fw={500}>
                    Map Controls:
                  </Text>
                  <Text size="sm">
                    •{' '}
                    <IconZoomIn
                      size={14}
                      style={{
                        display: 'inline',
                        verticalAlign: 'middle',
                      }}
                    />
                    <Text component="span" fw={500}>
                      {' '}
                      Zoom:
                    </Text>{' '}
                    Changes device detail level (PCS + DC Enclosures → PCS +
                    Strings)
                  </Text>
                  <Text size="sm">
                    •{' '}
                    <IconMouse
                      size={14}
                      style={{
                        display: 'inline',
                        verticalAlign: 'middle',
                      }}
                    />
                    <Text component="span" fw={500}>
                      {' '}
                      Hover:
                    </Text>{' '}
                    View device name, power values, and SOC
                  </Text>
                  <Text size="sm">
                    •{' '}
                    <IconLock
                      size={14}
                      style={{
                        display: 'inline',
                        verticalAlign: 'middle',
                      }}
                    />
                    <Text component="span" fw={500}>
                      {' '}
                      Lock View:
                    </Text>{' '}
                    Pin current zoom level to specific device type
                  </Text>
                  <Text size="sm">
                    •{' '}
                    <IconCursorText
                      size={14}
                      style={{
                        display: 'inline',
                        verticalAlign: 'middle',
                      }}
                    />
                    <Text component="span" fw={500}>
                      {' '}
                      Labels:
                    </Text>{' '}
                    Toggle device name labels on/off
                  </Text>
                  <Text size="sm">
                    •{' '}
                    <IconSatellite
                      size={14}
                      style={{
                        display: 'inline',
                        verticalAlign: 'middle',
                      }}
                    />
                    <Text component="span" fw={500}>
                      {' '}
                      Satellite:
                    </Text>{' '}
                    Switch between map and satellite view
                  </Text>
                  <Text size="sm">
                    <Text component="span" fw={500}>
                      Note:
                    </Text>{' '}
                    PCS charging shows a white glow effect, discharging shows a
                    green outline glow. Click on devices to view detailed
                    information.
                  </Text>
                </Stack>
              }
              fill
              style={{ flex: 1 }}
              key={projectId}
            >
              <AdaptiveGisBESS />
            </CustomCard>
            <BatteryHealth />
          </>
        </Stack>
        <Stack h="100%" flex={1}>
          {project.data.has_event_integration && (
            <TopEventsTableCard
              showLosses={
                project.data.project_type_id === ProjectTypeEnum.BESS ||
                project.data.has_expected_energy_integration
              }
            />
          )}
          <ContractualKPIOverview project={project.data} />
          <PowerPlotBESS />
        </Stack>
      </Group>

      {/* Project Information Modal */}
      <ProjectInfoModal
        opened={projectInfoModalOpen}
        onClose={() => setProjectInfoModalOpen(false)}
        projectData={project.data}
      />
    </Stack>
  )
}

function ProjectLabels({ projectId }: { projectId: string }) {
  const projectLabels = useGetUserProjectLabelsByProjectId({
    pathParams: { project_id: projectId },
  })

  if (!projectLabels.data?.length) {
    return null
  }

  return (
    <Group>
      {projectLabels.data.map((label) => (
        <Badge key={label.name} color={label.color} variant="light">
          {label.name}
        </Badge>
      ))}
    </Group>
  )
}

export default BESSProjectHome
