import { useGetTrackingAngles } from '@/api/v1/analytics/tracking-angles'
import { useGetCMMSTickets } from '@/api/v1/operational/project/cmms_tickets'
import {
  useGetEventLossesSummary,
  useGetEventTraceTags,
} from '@/api/v1/operational/project/events'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { useGetStatusTimeSeries } from '@/api/v1/operational/project/project_status'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import AriaRecommendation from '@/components/AriaRecommendation'
import CustomCard from '@/components/CustomCard'
import EventGISCard from '@/components/EventGISCard'
import { PageLoader } from '@/components/Loading'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { traceColors } from '@/components/plots/PlotlyPlotUtils'
import {
  useGetEvents,
  useGetFailureModes,
  useGetRootCauses,
  useUpdateRootCause,
} from '@/hooks/api'
import { useProjectDropdownToggle } from '@/hooks/custom'
import { Event } from '@/hooks/types'
import { BESSEnclosureGIS } from '@/pages/projects/gis/bess-enclosure-gis'
import {
  Badge,
  Button,
  Card,
  ComboboxItem,
  Group,
  HoverCard,
  Modal,
  OptionsFilter,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  Title,
  useMantineTheme,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconClock, IconInfoCircle } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { Dash } from 'plotly.js'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'

import { AdaptiveGisMap } from '../gis/adaptive-gis'
import { PCSGISMap } from '../gis/pcs-gis'
import DeviceEventsTimeline from './DeviceEventsTimeline'

// Types
interface EventTraceTag {
  tag_id: number
  device_id: number
  name_scada: string
  sensor_type?: {
    unit: string
    name_long: string
  }
  device?: {
    name_long: string
  }
}

interface RootCause {
  root_cause_id: number
  device_type_id: number
  name_long: string
  name_full?: string
}

// Utility function for string hashing
function stringToInt(str: string) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i)
    hash |= 0 // Convert to 32bit integer
  }
  return hash
}

// Custom hook for event data fetching
const useEventData = (projectId: string | undefined, eventId: number) => {
  const project = useSelectProject(projectId!)

  const eventData = useGetEvents({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryParams: {
      event_ids: [eventId],
      open: false,
    },
    queryOptions: {
      enabled: !!eventId && !!project.data,
    },
  })

  const eventLossesSummary = useGetEventLossesSummary({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { event_id: eventId },
    queryOptions: { enabled: !!eventId && !!projectId },
  })

  const event = eventData.data?.[0]

  const eventsHistorical = useGetEvents({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_id: event?.device_id?.toString(),
      open: false,
    },
    queryOptions: {
      enabled: !!event?.device_id,
    },
  })

  const CMMSTickets = useGetCMMSTickets({
    pathParams: { projectId: projectId || '-1' },
    queryParams: { device_ids: [event?.device_id || -1] },
    queryOptions: { enabled: !!event?.device_id },
  })

  const rootCauses = useGetRootCauses({
    pathParams: { projectId: projectId || '-1' },
  })

  const failureModes = useGetFailureModes({
    pathParams: { projectId: projectId || '-1' },
  })

  return {
    project,
    event,
    eventLossesSummary,
    eventsHistorical,
    CMMSTickets,
    rootCauses,
    failureModes,
    isLoading:
      project.isLoading || eventData.isLoading || eventLossesSummary.isLoading,
  }
}

// Event Header Component
const EventHeader = ({
  event,
  eventStatus,
  eventStartTime,
  eventEndTime,
  projectId,
}: {
  event: Event
  eventStatus: 'open' | 'closed' | 'unknown'
  eventStartTime: dayjs.Dayjs
  eventEndTime: dayjs.Dayjs
  projectId: string
}) => (
  <Stack>
    <Group>
      <Title order={2}>
        {event?.device.device_type_id === 29 ? (
          <>
            <Link
              to={`/projects/${projectId}/device-details/tracker-row/${event?.device_id}`}
              style={{ color: 'inherit' }}
            >
              {event?.device.device_type?.name_long} {event?.device.name_long}
            </Link>{' '}
            {' Event'}
          </>
        ) : (
          <>
            {event?.device.device_type?.name_long} {event?.device.name_long}{' '}
            {' Event'}
          </>
        )}
      </Title>
      <Badge color={eventStatus === 'open' ? 'red' : 'green'}>
        {eventStatus === 'open' ? 'Open' : 'Closed'}
      </Badge>
    </Group>
    <Badge color={'gray'} size="lg" variant="outline">
      <Group gap={2}>
        <IconClock size={16} />{' '}
        {dayjs(eventStartTime).format('MM/DD/YYYY HH:mm')} -{' '}
        {event?.time_end
          ? dayjs(eventEndTime).format('MM/DD/YYYY HH:mm')
          : 'ONGOING'}
      </Group>
    </Badge>
    <Text>
      {'Failure Mode: '}
      {event?.failure_mode?.name_long}
    </Text>
  </Stack>
)

// Event Losses Component
const EventLosses = ({
  losses,
}: {
  losses: Record<
    string,
    { title: string; value: string | number; unit: string; info?: string }
  >
}) => (
  <Table w="100%">
    <Table.Thead>
      <Table.Tr>
        <Table.Td>
          {losses.financial.title}
          {losses.financial.info && (
            <HoverCard>
              <HoverCard.Target>
                <IconInfoCircle size={10} />
              </HoverCard.Target>
              <HoverCard.Dropdown w="50%">
                <Text>{losses.financial.info}</Text>
              </HoverCard.Dropdown>
            </HoverCard>
          )}
        </Table.Td>
        <Table.Td>{losses.energetic.title}</Table.Td>
        <Table.Td>{losses.capacity.title}</Table.Td>
      </Table.Tr>
    </Table.Thead>
    <Table.Tbody>
      <Table.Tr>
        <Table.Td>
          <Text>
            {losses.financial.unit}
            {Number(losses.financial.value).toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </Text>
        </Table.Td>
        <Table.Td>
          <Text>
            {Number(losses.energetic.value).toLocaleString()}{' '}
            {losses.energetic.unit}
          </Text>
        </Table.Td>
        <Table.Td>
          <Text>
            {Number(losses.capacity.value).toLocaleString()}{' '}
            {losses.capacity.unit}
          </Text>
        </Table.Td>
      </Table.Tr>
    </Table.Tbody>
  </Table>
)

// Custom hook for event traces data
const useEventTraces = (
  projectId: string | undefined,
  event: Event | undefined,
  eventTraceTags: EventTraceTag[] | undefined,
  projectTz: string,
) => {
  const traceStart = dayjs(event?.time_start)
    .tz(projectTz)
    .subtract(1, 'day')
    .startOf('day')
  let traceEnd = dayjs(event?.time_end).isValid()
    ? dayjs(event?.time_end).tz(projectTz).endOf('day')
    : dayjs().tz(projectTz).endOf('day')
  if (traceEnd.diff(traceStart, 'days') > 3) {
    traceEnd = traceStart.add(3, 'days').endOf('day')
  }

  const eventTraces = useGetTimeSeries({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      tag_ids: eventTraceTags?.map((tag) => tag.tag_id) || [],
      start: traceStart.toISOString(),
      end: traceEnd.toISOString(),
    },
    queryOptions: { enabled: !!eventTraceTags?.length },
  })

  const statusTimeSeries = useGetStatusTimeSeries({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_ids: eventTraceTags?.map((tag) => tag.device_id || -1) || [],
      start: traceStart.toISOString(),
      end: traceEnd.toISOString(),
    },
    queryOptions: { enabled: !!eventTraceTags?.length },
  })

  const trueTrackingData = useGetTrackingAngles({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: traceStart.format('YYYY-MM-DD HH:mm:ss'),
      end: traceEnd.format('YYYY-MM-DD HH:mm:ss'),
    },
    queryOptions: {
      staleTime: Infinity, // Never expires
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      refetchOnReconnect: false,
      enabled: [28, 29].includes(event?.device.device_type_id || -1),
    },
  })

  return {
    eventTraces,
    statusTimeSeries,
    trueTrackingData,
    traceStart,
    traceEnd,
    isLoading:
      eventTraces.isLoading || !eventTraceTags || statusTimeSeries.isLoading,
  }
}

// Root Cause Selection Component
interface ConfirmRootModalProps {
  opened: boolean
  onClose: () => void
  onCancel: () => void
  selectedRootCause: number | null
  rootCauses?: { data?: RootCause[] }
  updateRootCause: (rootCauseId: number | null) => void
}

const ConfirmRootModal = ({
  opened,
  onClose,
  onCancel,
  selectedRootCause,
  rootCauses,
  updateRootCause,
}: ConfirmRootModalProps) => (
  <Modal
    opened={opened}
    onClose={onCancel}
    title={`Confirm Root Cause: ${
      rootCauses?.data?.find((fm) => fm.root_cause_id === selectedRootCause)
        ?.name_long ?? 'Unknown'
    }`}
    transitionProps={{ transition: 'rotate-left' }}
  >
    <Stack>
      <Text>Are you sure you want to change the root cause?</Text>
      <Group grow>
        <Button onClick={onCancel}>Cancel</Button>
        <Button
          onClick={() => {
            updateRootCause(selectedRootCause)
            onClose()
          }}
        >
          Confirm
        </Button>
      </Group>
    </Stack>
  </Modal>
)

const RootCauseSelection = ({
  event,
  showAllCauses,
  setShowAllCauses,
  selectedRootCause,
  setSelectedRootCause,
  rootCauses,
  rootCauseDeviceTypes,
  onRootCauseChange,
}: {
  event: Event | undefined
  showAllCauses: boolean
  setShowAllCauses: (show: boolean) => void
  selectedRootCause: number | null
  setSelectedRootCause: (cause: number | null) => void
  rootCauses: { data?: RootCause[] }
  rootCauseDeviceTypes: number[]
  onRootCauseChange: (cause: number | null) => void
}) => {
  const optionsFilter: OptionsFilter = ({ options, search }) => {
    const filtered = (options as ComboboxItem[]).filter((option) =>
      option.label.toLowerCase().includes(search.toLowerCase().trim()),
    )
    return filtered.sort((a, b) => a.label.localeCompare(b.label))
  }

  const shownRootCauses = showAllCauses
    ? rootCauses?.data
    : rootCauses?.data?.filter((rc) =>
        rootCauseDeviceTypes.includes(rc.device_type_id),
      )

  return (
    <>
      <Group>
        <Text>Root Cause:</Text>
        <Select
          w="60%"
          data={shownRootCauses?.map((fm) => ({
            value: fm.root_cause_id.toString(),
            label: fm.name_full || fm.name_long,
          }))}
          value={selectedRootCause?.toString()}
          onChange={(value) => {
            setSelectedRootCause(value ? parseInt(value) : null)
            if (value !== event?.root_cause_id?.toString()) {
              onRootCauseChange(value ? parseInt(value) : null)
            }
          }}
          clearable
          searchable
          nothingFoundMessage="Nothing found..."
          filter={optionsFilter}
        />
      </Group>
      <Switch
        label="Show All Root Causes"
        checked={showAllCauses}
        onChange={(event) => setShowAllCauses(event.currentTarget.checked)}
      />
    </>
  )
}

const Page = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const eventId = parseInt(
    new URLSearchParams(location.search).get('eventId') || '-1',
  )
  const [eventStatus, setEventStatus] = useState<'open' | 'closed' | 'unknown'>(
    'unknown',
  )
  const [showAllCauses, setShowAllCauses] = useState<boolean>(false)
  const [selectedRootCause, setSelectedRootCause] = useState<number | null>(
    null,
  )
  const [opened, { close, open }] = useDisclosure(false)
  const theme = useMantineTheme()

  useProjectDropdownToggle()

  const {
    project,
    event,
    eventLossesSummary,
    eventsHistorical,
    CMMSTickets,
    rootCauses,
    failureModes,
    isLoading: isPageLoading,
  } = useEventData(projectId, eventId)
  const projectTz = project.data?.time_zone || 'UTC'

  // If project.has_pv_dc_combiners is true, and we are on a PV DC Combiner (device_type_id 9) event,
  // allow root causes for DC Field (device_type_id 30).
  // If project.has_pv_dc_combiners is false, and we are on a PV PCS (device_type_id 2) event,
  // allow root causes for DC Field (device_type_id 30)
  // If we are on a PV PCS Module (device_type_id 3) event,
  // allow root causes for PV PCS (device_type_id 2)
  const rootCauseDeviceTypes: number[] = [event?.device?.device_type_id || -1]
  if (
    project.data?.has_pv_dc_combiners &&
    event?.device?.device_type_id === 9
  ) {
    rootCauseDeviceTypes.push(30)
  } else if (
    !project.data?.has_pv_dc_combiners &&
    event?.device?.device_type_id === 2
  ) {
    rootCauseDeviceTypes.push(30)
  }
  if (event?.device?.device_type_id === 3) {
    rootCauseDeviceTypes.push(2)
  }
  if (event?.device?.device_type_id === 29) {
    rootCauseDeviceTypes.push(28)
  }
  if (event?.device?.device_type_id === 28) {
    rootCauseDeviceTypes.push(29)
  }

  const mutation = useUpdateRootCause()
  const updateRootCause = (rootCauseId: number | null) => {
    mutation.mutate({
      project_id: projectId || '-1',
      event_id: eventId,
      root_cause_id: rootCauseId !== null ? rootCauseId : undefined,
    })
  }

  useEffect(() => {
    if (event) {
      queueMicrotask(() => setSelectedRootCause(event.root_cause_id))
    }
  }, [event])

  const eventTraceTags = useGetEventTraceTags({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_id: event?.device_id || -1,
    },
    queryOptions: { enabled: !!event?.device_id },
  })

  const {
    eventTraces,
    statusTimeSeries,
    trueTrackingData,
    traceStart,
    traceEnd,
    isLoading: isTracesLoading,
  } = useEventTraces(
    projectId,
    event,
    eventTraceTags.data as EventTraceTag[],
    projectTz,
  )

  // Process eventTraces.data for device type 28 to average Position and Setpoint traces
  let processedEventTraces = eventTraces.data
  if (event?.device.device_type_id === 28 && eventTraces.data) {
    // Group traces by name to identify Position and Setpoint traces
    const tracesByName = eventTraces.data.reduce<
      Record<string, typeof eventTraces.data>
    >((acc, trace) => {
      const traceName = trace.name

      if (!acc[traceName]) {
        acc[traceName] = []
      }
      acc[traceName].push(trace)
      return acc
    }, {})

    // Average Position and Setpoint traces
    const averagedTraces: typeof eventTraces.data = []

    Object.entries(tracesByName).forEach(([name, traces]) => {
      if (name === 'Position' || name === 'Setpoint') {
        if (traces.length > 1) {
          // Average multiple traces with the same name
          const firstTrace = traces[0]
          const averagedTrace = {
            ...firstTrace,
            x: firstTrace.x.filter((_, timeIndex) => {
              const values = traces
                .map((trace) => trace.y[timeIndex])
                .filter((value): value is number => value !== null)
              return values.length > 0
            }),
            y: firstTrace.x
              .map((_, timeIndex) => {
                const values = traces
                  .map((trace) => trace.y[timeIndex])
                  .filter((value): value is number => value !== null)

                if (values.length === 0) return null
                return values.reduce((sum, val) => sum + val, 0) / values.length
              })
              .filter((value): value is number => value !== null),
            device_name_long: event?.device.name_long || '',
          }
          averagedTraces.push(averagedTrace)
        } else {
          // Single trace, keep as-is
          averagedTraces.push(traces[0])
        }
      } else {
        // Other traces, keep as-is
        traces.forEach((trace) => averagedTraces.push(trace))
      }
    })

    processedEventTraces = averagedTraces
  }

  useEffect(() => {
    if (event?.time_end) {
      queueMicrotask(() => setEventStatus('closed'))
    } else {
      queueMicrotask(() => setEventStatus('open'))
    }
  }, [event?.time_end])

  const isTimelineLoading =
    eventsHistorical.isLoading || rootCauses.isLoading || CMMSTickets.isLoading

  if (isPageLoading) {
    return <PageLoader />
  }

  const eventStartTime = dayjs(event?.time_start).tz(project.data?.time_zone)
  const eventEndTime = dayjs(event?.time_end).tz(project.data?.time_zone)

  const currentType = [2, 3].includes(
    event?.device.device_type?.device_type_id || 0,
  )
    ? 'ac'
    : 'dc'
  const losses = {
    financial: {
      title: 'Daily Impact',
      value:
        (eventLossesSummary.data?.loss_daily_financial || 0)?.toFixed(2) ||
        ' N/A',
      unit: '$',
      info: 'Daily financial loss is calculated by dividing the total financial loss by the number of days in the event.\
      This calculation is sensitive to nuances such as other impacts to the project (including other Events) and daily expected production.\
      Financial loss is calculated as energy lost multiplied by the PPA price, as provided.',
    },
    energetic: {
      title: '',
      value:
        (eventLossesSummary.data?.loss_daily_energy || 0)?.toFixed(2) || ' N/A',
      unit: 'MWh',
    },
    capacity: {
      title: 'Capacity Loss',
      value:
        eventLossesSummary.data?.loss_capacity !== null &&
        eventLossesSummary.data?.loss_capacity !== undefined
          ? eventLossesSummary.data.loss_capacity
          : currentType === 'ac'
            ? event?.device.capacity_ac || 0
            : event?.device.capacity_dc || 0,
      unit:
        eventLossesSummary.data?.loss_capacity !== null &&
        eventLossesSummary.data?.loss_capacity !== undefined
          ? 'kW DC'
          : currentType === 'ac'
            ? 'kW AC'
            : 'kW DC',
    },
  }

  // Filter out traces with all null or empty object values
  const validTraces = (statusTimeSeries.data || [])
    .filter((trace) =>
      trace.y.some((value) => value !== null && value !== '{}'),
    )
    .sort((a, b) => (a.name || '').localeCompare(b.name || ''))

  // Combine all unique Y values where alert == true across all valid traces
  const uniqueY = Array.from(
    new Set(
      validTraces.flatMap((trace) =>
        trace.y.filter((_, idx) => trace.alert?.[idx]),
      ),
    ),
  )

  const heatmapData: {
    uniqueY: string[]
    x: string[]
    y: string[]
    z: number[][]
  } = {
    uniqueY,
    x: validTraces[0]?.x || [],
    y: validTraces.map((trace) => trace.name) || [],
    z:
      validTraces.map((trace) =>
        trace.alert.map((isAlert) => (isAlert ? 1 : 0)),
      ) || [],
  }
  const hasStatus = validTraces.length > 0

  // For heatmap, flatten the data for Plotly compatibility
  const flatZ: number[] = []
  const flatCustomData: [string][] = []
  const flatX: string[] = []
  const flatY: string[] = []
  heatmapData.z.forEach((row, rowIdx) => {
    row.forEach((zVal, colIdx) => {
      flatZ.push(zVal)
      const yValue = validTraces[rowIdx]?.y[colIdx] ?? null
      flatCustomData.push([
        typeof yValue === 'string'
          ? yValue.replace(/,/g, '<br>')
          : yValue || 'Unknown',
      ])
      flatX.push(heatmapData.x[colIdx])
      flatY.push(heatmapData.y[rowIdx])
    })
  })

  // Get unique units and create color mapping
  const uniqueUnits = Array.from(
    new Set(
      eventTraceTags.data
        ?.filter((tag) => !tag.name_scada.includes('status'))
        .map((tag) => tag.sensor_type?.unit ?? '') || [],
    ),
  ).sort((a, b) => {
    // Move empty string to the end
    if (a === '') return 1
    if (b === '') return -1
    return a.localeCompare(b)
  })

  const traceColorsArray = traceColors(theme)
  const unitColorMap = uniqueUnits.reduce(
    (acc, unit, index) => {
      acc[unit] = traceColorsArray[index]
      return acc
    },
    {} as Record<string, string>,
  )

  let mapComponent
  if (project.data?.project_type_id === ProjectTypeId.BESS) {
    mapComponent = <BESSEnclosureGIS showTitleCard={false} />
  } else if (
    projectId === '3028d2ee-c924-4c6e-a133-9938926bc4b6' ||
    projectId === '679f8f19-af11-43e0-9a60-64fc706f92a4'
  ) {
    mapComponent = <PCSGISMap showTitleCard={false} />
  } else {
    mapComponent = <AdaptiveGisMap />
  }

  // const annotations = [
  //   // Status annotations
  //   ...(hasStatus
  //     ? heatmapData.uniqueY.map((status, statusIndex) => {
  //         const firstTrueIndex = flatCustomData.findIndex(
  //           (data) => data[0] === status.replace(/,/g, '<br>'),
  //         )
  //         const firstX = flatX[firstTrueIndex]
  //         const firstY = flatY[firstTrueIndex]

  //         return {
  //           x: firstX,
  //           y: firstY,
  //           text: (status?.toString() || 'Unknown').replace(/,/g, '<br>'),
  //           showarrow: true,
  //           arrowhead: 2,
  //           arrowsize: 1,
  //           arrowwidth: 1,
  //           ax: 0,
  //           ay: statusIndex % 2 === 0 ? -20 : 20,
  //           font: { size: 10, color: '#fff' },
  //           bgcolor: 'rgba(0,0,0,0.7)',
  //           bordercolor: 'rgba(255,255,255,0.3)',
  //           borderwidth: 1,
  //           borderpad: 4,
  //           captureevents: true,
  //           xref: 'x' as const,
  //           yref: 'y2' as const,
  //         }
  //       })
  //     : []),
  // ]

  return (
    <Group h="100%" gap="md" p="md">
      <ConfirmRootModal
        opened={opened}
        onClose={close}
        onCancel={() => {
          close()
          setSelectedRootCause(event?.root_cause_id ?? null)
        }}
        selectedRootCause={selectedRootCause}
        rootCauses={rootCauses}
        updateRootCause={updateRootCause}
      />
      <Stack h="100%" flex={4}>
        <Group>
          <Stack>
            {event && (
              <EventHeader
                event={event}
                eventStatus={eventStatus}
                eventStartTime={eventStartTime}
                eventEndTime={eventEndTime}
                projectId={projectId || '-1'}
              />
            )}
            <RootCauseSelection
              event={event}
              showAllCauses={showAllCauses}
              setShowAllCauses={setShowAllCauses}
              selectedRootCause={selectedRootCause}
              setSelectedRootCause={setSelectedRootCause}
              rootCauses={rootCauses}
              rootCauseDeviceTypes={rootCauseDeviceTypes}
              onRootCauseChange={(cause) => {
                setSelectedRootCause(cause)
                open()
              }}
            />
            <EventLosses losses={losses} />
          </Stack>
          <CustomCard
            allowFullscreen={false}
            title="Aria Recommendation"
            style={{ height: '100%' }}
          >
            {event && losses.financial.value && (
              <AriaRecommendation
                event={event}
                dailyLoss={Number(losses.financial.value || 0)}
              />
            )}
          </CustomCard>
          <Group flex={1} h="100%" w="100%">
            <Card withBorder w="100%" h="100%" p={0} radius="md">
              {project.data?.spec.device_types_all_with_polygons?.includes(
                event?.device.device_type_id || -1,
              ) ? (
                <EventGISCard deviceId={event?.device_id.toString() || '-1'} />
              ) : (
                mapComponent
              )}
            </Card>
          </Group>
        </Group>

        <CustomCard title="Event Traces" fill style={{ height: '100%' }}>
          <PlotlyPlot
            isLoading={isTracesLoading && !eventTraceTags.error}
            data={[
              { yaxis: 'y' }, // Yes, we need this. No, I don't know why.
              ...(() => {
                // Group traces by sensor_type_id
                const tracesBySensorType = processedEventTraces?.reduce<
                  Record<
                    number,
                    Array<{
                      x: string[]
                      y: number[]
                      name: string
                      type: 'scatter'
                      line: { color: string; dash: Dash }
                      yaxis: string
                      hoverlabel: {
                        namelength: -1
                      }
                    }>
                  >
                >((acc, trace) => {
                  const tag = eventTraceTags.data?.find(
                    (tag) => tag.name_scada === trace.tag_name_scada,
                  )
                  if (
                    trace.sensor_type_name.includes('status') ||
                    trace.sensor_type_name.includes('alarm')
                  ) {
                    return acc
                  }

                  const unit = tag?.sensor_type?.unit ?? ''
                  const unitIndex = stringToInt(unit)
                  if (!acc[unitIndex]) {
                    acc[unitIndex] = []
                  }
                  acc[unitIndex].push({
                    x: trace.x.filter((_, index) => trace.y[index] !== null),
                    y: trace.y.filter(
                      (value): value is number => value !== null,
                    ),
                    name:
                      event?.device.device_type_id === 28
                        ? 'Average ' +
                          tag?.sensor_type?.name_long +
                          ' ' +
                          event?.device.name_long
                        : tag?.sensor_type?.name_long +
                          ' ' +
                          tag?.device?.name_long,
                    type: 'scatter' as const,
                    line: {
                      color: unitColorMap[unit] || traceColorsArray[0],
                      dash:
                        tag?.sensor_type_id === 25
                          ? ('dash' as const)
                          : ('solid' as const),
                    },
                    yaxis: unitIndex === 0 ? 'y' : `y${unitIndex + 1}`,
                    hoverlabel: {
                      namelength: -1,
                    },
                  })
                  return acc
                }, {})

                // Flatten the grouped traces and ensure each trace has a unique y-axis
                const traces = Object.entries(tracesBySensorType || {}).flatMap(
                  ([unitIndex, traces]) =>
                    traces.map((trace) => ({
                      ...trace,
                      yaxis:
                        parseInt(unitIndex) === 0
                          ? 'y'
                          : `y${parseInt(unitIndex) + 1}`,
                    })),
                )

                // If no traces were created, return empty array
                return traces || []
              })(),

              ...(hasStatus
                ? [
                    {
                      x: flatX,
                      y: flatY,
                      z: flatZ,
                      type: 'heatmap' as const,
                      yaxis: 'y2',
                      showscale: false,
                      zmin: 0,
                      zmax: 1,
                      colorscale: [
                        [0, theme.colors.green[7]],
                        [1, theme.colors.red[7]],
                      ] as [number, string][],
                      customdata: flatCustomData,
                      hovertemplate:
                        'Time: %{x}<br>Status: %{customdata[0]}<extra></extra>',
                      hoverlabel: {
                        namelength: -1,
                      },
                    },
                  ]
                : []),
              ...(trueTrackingData.data
                ? [
                    {
                      x: trueTrackingData.data.times,
                      y: trueTrackingData.data.tracker_theta,
                      name: 'Ideal Tracking Angle',
                      type: 'scatter' as const,
                      line: {
                        color: theme.colors.green[7],
                        dash: 'dot' as const,
                      },
                      yaxis: 'y',
                      hoverlabel: {
                        namelength: -1,
                      },
                    },
                  ]
                : []),
            ]}
            layout={{
              // annotations: annotations,
              shapes: [
                {
                  type: 'rect',
                  x0: eventStartTime.format('YYYY-MM-DD HH:mm:ss'),
                  x1:
                    eventEndTime.isValid() && eventEndTime <= traceEnd
                      ? eventEndTime.format('YYYY-MM-DD HH:mm:ss')
                      : traceEnd.format('YYYY-MM-DD HH:mm:ss'),
                  y0: hasStatus ? 0.575 : 0,
                  y1: 1,
                  xref: 'x',
                  yref: 'paper',
                  fillcolor: 'rgba(255, 0, 0, 0.3)',
                  line: {
                    width: 0,
                  },
                },
              ],
              grid: {
                rows: hasStatus ? 2 : 1,
                columns: 1,
                pattern: 'independent',
              },
              // Base y-axis configuration for the main plot area
              yaxis: {
                title: {
                  text: (() => {
                    const units = Array.from(
                      new Set(
                        eventTraceTags.data
                          ?.filter((tag) => !tag.name_scada.includes('status'))
                          .map((tag) => tag.sensor_type?.unit ?? '') || [],
                      ),
                    ).filter((unit) => unit !== '')

                    if (units.length === 0) {
                      return 'Value'
                    } else if (units.length === 1) {
                      return units[0]
                    } else {
                      return 'Value'
                    }
                  })(),
                  font: { color: theme.colors.blue[6] },
                },
                side: 'left',
                domain: hasStatus ? [0.55, 1] : [0, 1],
                showgrid: false,
                zeroline: false,
                automargin: true,
                visible: false,
                tickformat: (() => {
                  const units = Array.from(
                    new Set(
                      eventTraceTags.data
                        ?.filter((tag) => !tag.name_scada.includes('status'))
                        .map((tag) => tag.sensor_type?.unit ?? '') || [],
                    ),
                  ).filter((unit) => unit !== '')

                  // Apply tickformat only if there's exactly one unit
                  if (units.length === 1) {
                    return units[0] === '%' ? ',.0%' : undefined
                  }
                  return undefined
                })(),
              },
              yaxis2: {
                domain: hasStatus ? [0, 0.45] : [0, 1],
                range: [
                  traceStart.format('YYYY-MM-DD HH:mm:ss'),
                  traceEnd.format('YYYY-MM-DD HH:mm:ss'),
                ],
                title: {
                  text: 'Status',
                  font: { color: theme.colors.gray[6] },
                },
                showgrid: false,
                zeroline: false,
              },
              // Add y-axes for each unit
              ...(() => {
                const units = Array.from(
                  new Set(
                    eventTraceTags.data
                      ?.filter((tag) => !tag.name_scada.includes('status'))
                      .map((tag) => tag.sensor_type?.unit ?? '') || [],
                  ),
                ).filter((unit) => unit !== '') // Filter out empty units

                // If no units found, return empty object to avoid creating unnecessary axes
                if (units.length === 0) {
                  return {}
                }

                return units.reduce<
                  Record<
                    string,
                    {
                      title: { text: string; font: { color: string } }
                      side: 'left' | 'right'
                      overlaying: string
                      showgrid: boolean
                      zeroline: boolean
                      position: number
                      anchor: 'free'
                      autoshift: boolean
                      tickformat?: string
                    }
                  >
                >((acc, unit, index) => {
                  const unitIndex = stringToInt(unit)
                  const axisName = `yaxis${unitIndex + 1}`
                  const color = unitColorMap[unit] || traceColorsArray[0]
                  acc[axisName] = {
                    title: {
                      text: unit || 'Unitless',
                      font: { color },
                    },
                    side: index % 2 === 0 ? 'left' : 'right',
                    overlaying: 'y',
                    showgrid: false,
                    zeroline: false,
                    position: index % 2 === 0 ? 0 : 1,
                    anchor: 'free',
                    autoshift: true,
                    tickformat: unit === '%' ? ',.0%' : undefined,
                  }
                  return acc
                }, {})
              })(),
            }}
            error={eventTraceTags.error}
          />
        </CustomCard>
      </Stack>
      <Stack h="100%" flex={1}>
        <CustomCard
          allowFullscreen={false}
          title="Timeline"
          style={{ height: '100%' }}
        >
          <DeviceEventsTimeline
            isLoading={isTimelineLoading}
            events={eventsHistorical.data || []}
            failureModes={failureModes.data || []}
            projectId={projectId || '-1'}
            selectedEvent={event || ({} as Event)}
            tickets={CMMSTickets.data?.data}
          />
        </CustomCard>
      </Stack>
    </Group>
  )
}

export default Page
