import { useGetOperationalKPIData } from '@/api/v1/operational/kpi_data'
import { useGetKPITypes } from '@/api/v1/operational/kpi_types'
import { useGetProject } from '@/api/v1/operational/projects'
import {
  EventMetrics,
  useGetEventsMetaAnalysis,
} from '@/api/v1/protected/web-application/projects/events/events'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import {
  Badge,
  Box,
  Divider,
  Group,
  Modal,
  Paper,
  SegmentedControl,
  Stack,
  Text,
  Title,
  Tooltip,
} from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { PlotMouseEvent } from 'plotly.js/dist/plotly-custom.min.js'
import { useCallback, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'

type DateRangeOption =
  | 'Week to Date'
  | 'Month to Date'
  | 'Year to Date'
  | 'BOL to Date'
const DATE_RANGE_OPTIONS: DateRangeOption[] = [
  'Week to Date',
  'Month to Date',
  'Year to Date',
  'BOL to Date',
]

const Page = () => {
  const { projectId } = useParams()
  const [selectedDateRange, setSelectedDateRange] =
    useState<DateRangeOption>('Month to Date')
  const [modalOpened, setModalOpened] = useState(false)
  const [selectedDeviceType, setSelectedDeviceType] =
    useState<EventMetrics | null>(null)

  const project = useGetProject({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryOptions: { enabled: !!projectId },
  })

  // ---- Window calculation (unchanged semantics) ----
  const { startDate, endDate } = useMemo(() => {
    const tz = project.data?.time_zone
    const end = dayjs().tz(tz).startOf('hour')
    let start: dayjs.Dayjs

    switch (selectedDateRange) {
      case 'Week to Date':
        start = end.startOf('week')
        break
      case 'Month to Date':
        start = end.startOf('month')
        break
      case 'Year to Date':
        start = end.startOf('year')
        break
      case 'BOL to Date':
        start = dayjs(project.data?.cod).tz(tz)
        break
      default:
        start = end.startOf('day')
        break
    }
    return { startDate: start, endDate: end }
  }, [project.data?.time_zone, project.data?.cod, selectedDateRange])

  // ---- Queries ----
  const eventsMetaAnalysis = useGetEventsMetaAnalysis({
    pathParams: { projectId: projectId as string },
    queryParams: {
      start: startDate.toISOString(),
      end: endDate.toISOString(),
    },
    queryOptions: { enabled: !!projectId },
  })

  const availabilityData = useGetOperationalKPIData({
    queryParams: {
      start: startDate.format('YYYY-MM-DD'),
      end: endDate.format('YYYY-MM-DD'),
      project_ids: [projectId as string],
      kpi_type_ids: [1, 34, 57, 58],
    },
    queryOptions: { enabled: !!projectId },
  })

  const kpiTypeData = useGetKPITypes({
    queryParams: { kpi_type_ids: [1, 34, 57, 58] },
  })

  // Map KPI data with names; keep same shape and fallback logic
  const kpiDataByType = useMemo(() => {
    if (!availabilityData.data) return undefined
    return availabilityData.data.map((data) => {
      const kpiType = kpiTypeData.data?.find(
        (kt) => kt.kpi_type_id === data.kpi_type_id,
      )
      return {
        kpi_type_id: data.kpi_type_id,
        kpi_type_name: kpiType?.name_long,
        data: {
          ...data.data,
          project_data: data.data.project_data?.map((v) => v ?? 0) || [],
        },
      }
    })
  }, [availabilityData.data, kpiTypeData.data])

  // Convenience refs
  const metrics: EventMetrics[] = eventsMetaAnalysis.data?.metrics ?? []
  const metricsByName = useMemo(() => {
    const map = new Map<string, EventMetrics>()
    metrics.forEach((m) => map.set(m.device_type_name, m))
    return map
  }, [metrics])

  // ---- Click handler (identical behavior) ----
  const handlePlotClick = useCallback(
    (event: Readonly<PlotMouseEvent>) => {
      if (event.points && event.points.length > 0) {
        const point = event.points[0]
        const deviceTypeName = point.x as string
        const deviceTypeData = metricsByName.get(deviceTypeName)
        if (deviceTypeData) {
          setSelectedDeviceType(deviceTypeData)
          setModalOpened(true)
        }
      }
    },
    [metricsByName],
  )

  // ---- MTBF chart data (filter > 0, sort ascending) ----
  const mtbfData = useMemo(() => {
    if (!metrics.length) return []
    const filtered = metrics
      .filter((m) => (m.MTBF_hours ?? 0) > 0)
      .sort((a, b) => (a.MTBF_hours ?? 0) - (b.MTBF_hours ?? 0))
    return [
      {
        y: filtered.map((m) => m.MTBF_hours ?? 0),
        x: filtered.map((m) => m.device_type_name),
        type: 'bar' as const,
        name: 'MTBF',
      },
    ]
  }, [metrics])

  // ---- MTTR chart data (sort ascending) ----
  const mttrData = useMemo(() => {
    if (!metrics.length) return []
    const sorted = [...metrics].sort(
      (a, b) => (a.MTTR_hours ?? 0) - (b.MTTR_hours ?? 0),
    )
    return [
      {
        y: sorted.map((m) => m.MTTR_hours ?? 0),
        x: sorted.map((m) => m.device_type_name),
        type: 'bar' as const,
        name: 'MTTR',
      },
    ]
  }, [metrics])

  // ---- Failure Count & Unavailability (sorted by unavailability desc) ----
  const { combinedChartData } = useMemo(() => {
    if (!metrics.length) {
      return {
        combinedChartData: [],
      }
    }

    const sortedByUnavail = [...metrics].sort(
      (a, b) =>
        (b.unavailability_contribution ?? 0) -
        (a.unavailability_contribution ?? 0),
    )

    const failureCountDataLocal = [
      {
        x: sortedByUnavail.map((m) => m.device_type_name),
        y: sortedByUnavail.map((m) => m.failure_count),
        type: 'bar' as const,
        name: 'Failure Count',
        yaxis: 'y',
      },
    ]

    const unavailabilityDataLocal = [
      {
        x: sortedByUnavail.map((m) => m.device_type_name),
        y: sortedByUnavail.map((m) => m.unavailability_contribution),
        type: 'scatter' as const,
        mode: 'lines+markers' as const,
        name: 'Unavailability Contribution',
        yaxis: 'y2',
        line: { color: '#fa5252', width: 3 },
        marker: { size: 8, color: '#fa5252' },
      },
    ]

    return {
      failureCountData: failureCountDataLocal,
      unavailabilityContributionsData: unavailabilityDataLocal,
      combinedChartData: [...failureCountDataLocal, ...unavailabilityDataLocal],
    }
  }, [metrics])

  // ---- Project Availability / PR trace (preserve original priority & styling) ----
  const projectAvailabilityData = useMemo(() => {
    if (!kpiDataByType || kpiDataByType.length === 0) {
      return { data: [], isPerformanceRatio: false as const }
    }

    const projectAvailabilityKPI = kpiDataByType.find(
      (k) => k.kpi_type_id === 34,
    )

    if (
      projectAvailabilityKPI?.data?.dates &&
      projectAvailabilityKPI.data.project_data
    ) {
      return {
        data: [
          {
            x: projectAvailabilityKPI.data.dates,
            y: projectAvailabilityKPI.data.project_data,
            type: 'scatter' as const,
            name: 'Performance Ratio',
            color: '#FFFFFF',
            line: { dash: 'dash' as const },
            yaxis: 'y',
          },
        ],
        isPerformanceRatio: true as const,
      }
    }

    // Fallback: average across KPI types per date
    const allDates = new Set<string>()
    kpiDataByType.forEach((k) => {
      k.data?.dates?.forEach((d: string) => allDates.add(d))
    })
    const sortedDates = Array.from(allDates).sort()

    const combined = sortedDates.map((date) => {
      let sum = 0
      let count = 0
      kpiDataByType.forEach((k) => {
        const dates = k.data?.dates
        const values = k.data?.project_data
        if (dates && values) {
          const idx = dates.indexOf(date)
          if (idx !== -1) {
            sum += values[idx]
            count++
          }
        }
      })
      return { x: date, y: count > 0 ? sum / count : 0 }
    })

    return {
      data: [
        {
          x: combined.map((d) => d.x),
          y: combined.map((d) => d.y),
          type: 'scatter' as const,
          name: 'Project Availability',
          color: '#FFFFFF',
          line: { dash: 'dash' as const },
          yaxis: 'y',
        },
      ],
      isPerformanceRatio: false as const,
    }
  }, [kpiDataByType])

  // ---- Daily totals (preserve original filter window semantics) ----
  const dailyTotalsData = useMemo(() => {
    const totals = eventsMetaAnalysis.data?.daily_totals
    const tz = project.data?.time_zone
    if (!totals?.dates || !totals?.counts) return []

    const filtered = totals.dates
      .map((date, i) => ({
        date: dayjs(date).tz(tz),
        count: totals.counts[i],
      }))
      .filter(
        ({ date }) =>
          date.isAfter(startDate) && date.isBefore(endDate.add(1, 'day')),
      )
      .map(({ date, count }) => ({
        x: date.format('YYYY-MM-DD'),
        y: count,
      }))

    return [
      {
        x: filtered.map((d) => d.x),
        y: filtered.map((d) => d.y),
        type: 'bar' as const,
        name: 'Daily Events',
        yaxis: 'y2',
        marker: { color: '#fa5252', opacity: 0.7 },
        orientation: 'v' as const,
      },
    ]
  }, [
    eventsMetaAnalysis.data?.daily_totals,
    project.data?.time_zone,
    startDate,
    endDate,
  ])

  const compoundChartData = useMemo(
    () => [...projectAvailabilityData.data, ...dailyTotalsData],
    [projectAvailabilityData.data, dailyTotalsData],
  )

  // ---- Loading gate ----
  if (project.isLoading) return <PageLoader />

  return (
    <Stack p="md" h="100%">
      <DeviceTypeModal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        deviceTypeData={selectedDeviceType}
        deviceTotalsData={eventsMetaAnalysis.data?.device_totals?.find(
          (total) =>
            total.device_type_id === selectedDeviceType?.device_type_id,
        )}
      />
      <Group justify="space-between">
        <Title>Events Meta-Analysis</Title>
        <SegmentedControl
          data={DATE_RANGE_OPTIONS}
          value={selectedDateRange}
          onChange={(value) => setSelectedDateRange(value as DateRangeOption)}
        />
      </Group>
      <Group h="100%">
        <Stack h="100%" flex={1}>
          <CustomCard
            title={
              projectAvailabilityData.isPerformanceRatio
                ? 'Performance Ratio & Events per Day'
                : 'Project Availability & Events per Day'
            }
            style={{ height: '100%' }}
            headerChildren={
              !projectAvailabilityData.isPerformanceRatio ? (
                <Tooltip label="Project Availability is still under development. It is currently calculated as the average availability of all component-level availability calculations, but will become capacity-weighted and more detailed as further KPIs are added.">
                  <IconAlertTriangle color="orange" />
                </Tooltip>
              ) : undefined
            }
          >
            <PlotlyPlot
              data={compoundChartData}
              layout={{
                xaxis: { title: 'Date' },
                yaxis: {
                  title: projectAvailabilityData.isPerformanceRatio
                    ? 'Performance Ratio (%)'
                    : 'Availability (%)',
                  range: [0, 1.025],
                  tickformat: ',.2%',
                },
                yaxis2: {
                  title: 'Daily Events',
                  overlaying: 'y',
                  side: 'right',
                  showgrid: false,
                },
                margin: { l: 60, r: 60, t: 30, b: 60 },
              }}
              isLoading={
                availabilityData.isLoading || eventsMetaAnalysis.isLoading
              }
            />
          </CustomCard>

          {project.data?.project_type_id != 2 && (
            <CustomCard
              title="Inverter Availability"
              style={{ height: '100%' }}
            >
              <PlotlyPlot
                data={kpiDataByType
                  ?.filter((k) => [1].includes(k.kpi_type_id))
                  .map((k) => ({
                    x: k.data.dates,
                    y: k.data.project_data,
                    type: 'scatter' as const,
                    name: k.kpi_type_name,
                  }))}
                layout={{
                  xaxis: { title: 'Date' },
                  yaxis: {
                    title: 'Availability (%)',
                    range: [0, 1.025],
                    tickformat: ',.2%',
                  },
                  margin: { l: 60, r: 30, t: 30, b: 60 },
                }}
                isLoading={availabilityData.isLoading}
              />
            </CustomCard>
          )}

          {project.data?.project_type_id != 1 && (
            <CustomCard title="BESS Availability" style={{ height: '100%' }}>
              <PlotlyPlot
                data={kpiDataByType
                  ?.filter((k) => [57, 58].includes(k.kpi_type_id))
                  .map((k) => ({
                    x: k.data.dates,
                    y: k.data.project_data,
                    type: 'scatter' as const,
                    name: k.kpi_type_name,
                  }))}
                layout={{
                  xaxis: { title: 'Date' },
                  yaxis: {
                    title: 'Availability (%)',
                    range: [0, 1.025],
                    tickformat: ',.2%',
                  },
                  margin: { l: 60, r: 30, t: 30, b: 60 },
                }}
                isLoading={availabilityData.isLoading}
              />
            </CustomCard>
          )}
        </Stack>

        <Stack h="100%" flex={2}>
          <CustomCard
            title="Equipment Failures and Unavailability Contributions"
            style={{ height: '100%' }}
            info="Click on a device type to view more details."
          >
            <PlotlyPlot
              data={combinedChartData}
              layout={{
                xaxis: { title: 'Device Type' },
                yaxis: { title: 'Failure Count' },
                yaxis2: {
                  title: 'Unavailability Contribution (%)',
                  overlaying: 'y',
                  side: 'right',
                  showgrid: false,
                  tickformat: ',.2%',
                },
                margin: { l: 60, r: 30, t: 30, b: 60 },
                height: 300,
              }}
              isLoading={eventsMetaAnalysis.isLoading}
              onClick={handlePlotClick}
            />
          </CustomCard>

          <Group grow h="100%">
            <CustomCard
              title="Mean Time Between Failures"
              style={{ height: '100%' }}
            >
              {mtbfData[0]?.x?.length || eventsMetaAnalysis.isLoading ? (
                <PlotlyPlot
                  data={mtbfData}
                  layout={{
                    xaxis: { title: 'Device Type' },
                    yaxis: { title: 'Hours' },
                  }}
                  isLoading={eventsMetaAnalysis.isLoading}
                />
              ) : (
                <Group justify="center" align="center" h="100%">
                  <Text size="xl">Insufficient data for MTBF calculation.</Text>
                </Group>
              )}
            </CustomCard>

            <CustomCard title="Mean Time to Repair" style={{ height: '100%' }}>
              {mtbfData[0]?.x?.length || eventsMetaAnalysis.isLoading ? (
                <PlotlyPlot
                  data={mttrData}
                  layout={{
                    xaxis: { title: 'Device Type' },
                    yaxis: { title: 'Hours' },
                  }}
                  isLoading={eventsMetaAnalysis.isLoading}
                />
              ) : (
                <Group justify="center" align="center" h="100%">
                  <Text size="xl">Insufficient data for MTTR calculation.</Text>
                </Group>
              )}
            </CustomCard>
          </Group>
        </Stack>
      </Group>
    </Stack>
  )
}

interface DeviceTypeModalProps {
  opened: boolean
  onClose: () => void
  deviceTypeData?: EventMetrics | null
  deviceTotalsData?: {
    device_type_id: number
    device_ids: number[]
    device_names: string[]
    total_failures: number[]
    total_hours: number[]
  } | null
}

const DeviceTypeModal = ({
  opened,
  onClose,
  deviceTypeData,
  deviceTotalsData,
}: DeviceTypeModalProps) => {
  if (!deviceTypeData) return null

  const [selectedTotalType, setSelectedTotalType] = useState<
    'total_failures' | 'total_hours'
  >('total_failures')

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Text size="xl" fw={600}>
          Device Type: {deviceTypeData.device_type_name}
        </Text>
      }
      size="xl"
      h="100%"
    >
      <Stack gap="md" h="100%">
        <Group justify="space-between" align="center">
          <Text size="sm" c="dimmed">
            Device Type ID:
          </Text>
          <Badge variant="light" size="lg">
            {deviceTypeData.device_type_id}
          </Badge>
        </Group>

        <Divider />

        <Title order={4} mb="md">
          Performance Metrics
        </Title>

        <Group justify="space-between">
          <Text size="sm" c="dimmed">
            Failure Count:
          </Text>
          <Text size="sm" fw={500}>
            {deviceTypeData.failure_count.toLocaleString()}
          </Text>
        </Group>

        {deviceTypeData.unavailability_contribution && (
          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              Unavailability Contribution:
            </Text>
            <Text size="sm" fw={500}>
              {(deviceTypeData.unavailability_contribution * 100).toFixed(2)}%
            </Text>
          </Group>
        )}

        {deviceTypeData.MTBF_hours && (
          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              Mean Time Between Failures (MTBF):
            </Text>
            <Text size="sm" fw={500}>
              {deviceTypeData.MTBF_hours.toFixed(1)} hours
            </Text>
          </Group>
        )}

        {deviceTypeData.MTTR_hours && (
          <Group justify="space-between">
            <Text size="sm" c="dimmed">
              Mean Time to Repair (MTTR):
            </Text>
            <Text size="sm" fw={500}>
              {deviceTypeData.MTTR_hours.toFixed(1)} hours
            </Text>
          </Group>
        )}

        <Paper withBorder>
          <Stack align="center" py="md">
            <SegmentedControl
              data={[
                { value: 'total_failures', label: 'Failure Count' },
                { value: 'total_hours', label: 'Hours Unavailable' },
              ]}
              value={selectedTotalType}
              onChange={(value) =>
                setSelectedTotalType(value as 'total_failures' | 'total_hours')
              }
            />
            <Box w="100%" h={500}>
              <PlotlyPlot
                data={[
                  {
                    x: deviceTotalsData?.device_names,
                    y:
                      selectedTotalType === 'total_failures'
                        ? deviceTotalsData?.total_failures
                        : deviceTotalsData?.total_hours,
                    type: 'bar' as const,
                    name:
                      selectedTotalType === 'total_failures'
                        ? 'Failure Count'
                        : 'Hours Unavailable',
                  },
                ]}
                layout={{
                  xaxis: { title: 'Device Name' },
                  yaxis: {
                    title:
                      selectedTotalType === 'total_failures'
                        ? 'Failure Count'
                        : 'Hours Unavailable',
                  },
                  autosize: true,
                }}
              />
            </Box>
          </Stack>
        </Paper>
      </Stack>
    </Modal>
  )
}

export default Page
