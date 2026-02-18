import { DeviceTypeEnum } from '@/api/enumerations'
import { useGetFailureModes } from '@/api/v1/operational/failure_modes'
import { useGetCMMSTickets } from '@/api/v1/operational/project/cmms_tickets'
import { useGetEventLossesSummary } from '@/api/v1/operational/project/events'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetRootCauses } from '@/api/v1/operational/root_causes'
import { useGetUtilityExpected } from '@/api/v1/protected/pv-expected-energy/plot/plot'
import CustomCard from '@/components/CustomCard'
import { EventChat } from '@/components/EventChat'
import { PageLoader } from '@/components/Loading'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetDevicesV2, useGetEvents, useUpdateRootCause } from '@/hooks/api'
import { useProjectDropdownToggle } from '@/hooks/custom'
import { Event } from '@/hooks/types'
import {
  Badge,
  Button,
  ComboboxItem,
  Group,
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
import { IconClock } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState } from 'react'
import { useLocation, useParams } from 'react-router'

import DcFieldAnomaliesMap from './DcFieldAnomaliesMap'
import DeviceEventsTimeline from './DeviceEventsTimeline'

// Types

interface RootCause {
  root_cause_id: number
  device_type_id: number
  name_long: string
  name_full?: string
}

// Helper function to calculate moving average
const calculateMovingAverage = (
  data: Array<number | null | string>,
  windowSize: number,
): Array<number | null> => {
  if (data.length === 0) return []

  const result: Array<number | null> = []
  const halfWindow = Math.floor(windowSize / 2)

  for (let i = 0; i < data.length; i++) {
    const start = Math.max(0, i - halfWindow)
    const end = Math.min(data.length, i + halfWindow + 1)
    const window = data.slice(start, end)
    const numericValues = window
      .map((value) => {
        if (typeof value === 'number') return value
        if (typeof value === 'string') return Number(value)
        return null
      })
      .filter((value): value is number => Number.isFinite(value))
    if (numericValues.length === 0) {
      result.push(null)
      continue
    }
    const average =
      numericValues.reduce((sum, val) => sum + val, 0) / numericValues.length
    result.push(average)
  }

  return result
}

// Custom hook for DC Field event data fetching
const useDcFieldEventData = (
  projectId: string | undefined,
  eventId: number,
) => {
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
    pathParams: { project_id: projectId || '-1' },
    queryParams: { device_ids: [event?.device_id || -1] },
    queryOptions: { enabled: !!event?.device_id },
  })

  const rootCauses = useGetRootCauses({})

  const failureModes = useGetFailureModes({})

  // Get devices to find the DC combiner (same pattern as ExpectedPlotting)
  const devices = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      device_type_ids: [
        DeviceTypeEnum.METER,
        DeviceTypeEnum.PV_PCS,
        DeviceTypeEnum.PV_DC_COMBINER,
      ],
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  // Find the DC combiner device (parent of the DC field)
  const dcCombinerDevice = devices.data?.find(
    (device) => device.device_id === event?.device?.parent_device_id,
  )

  // Calculate date range: 2 days before and after event start
  const eventStartTime = event?.time_start ? dayjs(event.time_start) : null
  const expectedStart = eventStartTime?.subtract(0, 'days').startOf('day')
  const expectedEnd = eventStartTime?.add(2, 'days').endOf('day')

  // Convert to ISO strings (same pattern as ExpectedPlotting)
  let startQuery: string | undefined = undefined
  let endQuery: string | undefined = undefined
  if (project.data) {
    if (expectedStart) {
      startQuery = expectedStart.tz(project.data.time_zone, true).toISOString()
    }
    if (expectedEnd) {
      endQuery = expectedEnd.tz(project.data.time_zone, true).toISOString()
    }
  }

  // Get expected power data for the DC combiner (same pattern as ExpectedPlotting)
  const expectedPower = useGetUtilityExpected({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      device_id: dcCombinerDevice?.device_id || -1,
      start: startQuery || '',
      end: endQuery || '',
      warranted_degradation: false,
    },
    queryOptions: {
      enabled: !!dcCombinerDevice && !!expectedStart && !!expectedEnd,
    },
  })

  return {
    project,
    event,
    eventLossesSummary,
    eventsHistorical,
    CMMSTickets,
    rootCauses,
    failureModes,
    dcCombinerDevice,
    expectedPower,
    isLoading:
      project.isLoading || eventData.isLoading || eventLossesSummary.isLoading,
  }
}

// DC Field Event Header Component
const DcFieldEventHeader = ({
  event,
  eventStatus,
  eventStartTime,
  eventEndTime,
}: {
  event: Event
  eventStatus: 'open' | 'closed' | 'unknown'
  eventStartTime: dayjs.Dayjs
  eventEndTime: dayjs.Dayjs
}) => (
  <Stack>
    <Group>
      <Title order={2}>
        {event?.device?.device_type?.name_long} {event?.device?.name_long}{' '}
        {' Event'}
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
    { title: string; value: string | number; unit: string }
  >
}) => (
  <Table w="100%">
    <Table.Thead>
      <Table.Tr>
        <Table.Td>{losses.financial.title}</Table.Td>
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

// Root Cause Selection Component for DC Field
const DcFieldRootCauseSelection = ({
  event,
  showAllCauses,
  setShowAllCauses,
  selectedRootCause,
  setSelectedRootCause,
  rootCauses,
  onRootCauseChange,
}: {
  event: Event | undefined
  showAllCauses: boolean
  setShowAllCauses: (show: boolean) => void
  selectedRootCause: number | null
  setSelectedRootCause: (cause: number | null) => void
  rootCauses: { data?: RootCause[] }
  onRootCauseChange: (cause: number | null) => void
}) => {
  const optionsFilter: OptionsFilter = ({ options, search }) => {
    const filtered = (options as ComboboxItem[]).filter((option) =>
      option.label.toLowerCase().includes(search.toLowerCase().trim()),
    )
    return filtered.sort((a, b) => a.label.localeCompare(b.label))
  }

  // For DC Field events, allow root causes for DC Field (device_type_id 30)
  // and related device types like PV PCS (2) and PV DC Combiner (9)
  const rootCauseDeviceTypes = [30, 2, 9]
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

// Confirm Root Cause Modal Component
const ConfirmRootModal = ({
  opened,
  onClose,
  selectedRootCause,
  rootCauses,
  onConfirm,
}: {
  opened: boolean
  onClose: () => void
  selectedRootCause: number | null
  rootCauses: { data?: RootCause[] }
  onConfirm: () => void
}) => (
  <Modal
    opened={opened}
    onClose={onClose}
    title={`Confirm Root Cause: ${
      rootCauses?.data?.find((fm) => fm.root_cause_id === selectedRootCause)
        ?.name_long ?? 'Unknown'
    }`}
    transitionProps={{ transition: 'rotate-left' }}
  >
    <Stack>
      <Text>Are you sure you want to change the root cause?</Text>
      <Group grow>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={onConfirm}>Confirm</Button>
      </Group>
    </Stack>
  </Modal>
)

const Page = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const location = useLocation()
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
    dcCombinerDevice,
    expectedPower,
    isLoading: isPageLoading,
  } = useDcFieldEventData(projectId, eventId)
  const projectTz = project.data?.time_zone || 'UTC'

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

  useEffect(() => {
    if (event?.time_end) {
      queueMicrotask(() => setEventStatus('closed'))
    } else {
      queueMicrotask(() => setEventStatus('open'))
    }
  }, [event?.time_end])

  const isTimelineLoading =
    eventsHistorical.isLoading || rootCauses.isLoading || CMMSTickets.isLoading

  const eventStartTime = dayjs(event?.time_start).tz(projectTz)
  const eventEndTime = dayjs(event?.time_end).tz(projectTz)

  // Calculate trace date range for the plot
  const traceEnd = eventStartTime.add(2, 'days').endOf('day')

  // Calculate moving average for power difference data
  const powerDifference =
    expectedPower.data?.expected_soiled?.difference ?? null
  const powerDifferenceMovingAverage = useMemo(() => {
    if (!powerDifference) return []
    return calculateMovingAverage(powerDifference, 20)
  }, [powerDifference])

  if (isPageLoading) {
    return <PageLoader />
  }

  // DC Field events are typically DC type
  const losses = {
    financial: {
      title: 'Daily Impact',
      value:
        eventLossesSummary.data?.loss_daily_financial != null
          ? eventLossesSummary.data.loss_daily_financial.toFixed(2)
          : 'N/A',
      unit: '$',
    },
    energetic: {
      title: '',
      value:
        eventLossesSummary.data?.loss_daily_energy != null
          ? eventLossesSummary.data.loss_daily_energy.toFixed(2)
          : 'N/A',
      unit: 'MWh',
    },
    capacity: {
      title: 'PV DC Capacity Loss',
      value:
        eventLossesSummary.data?.loss_capacity !== null &&
        eventLossesSummary.data?.loss_capacity !== undefined
          ? eventLossesSummary.data.loss_capacity?.toFixed(2)
          : (event?.device?.capacity_dc || 0)?.toFixed(2),
      unit: 'kW DC',
    },
  }

  return (
    <>
      <ConfirmRootModal
        opened={opened}
        onClose={() => {
          close()
          setSelectedRootCause(event?.root_cause_id ?? null)
        }}
        selectedRootCause={selectedRootCause}
        rootCauses={rootCauses}
        onConfirm={() => {
          updateRootCause(selectedRootCause)
          close()
        }}
      />
      <Group gap="md" p="md" align="stretch">
        <Stack flex={1}>
          <Group align="flex-start" style={{ alignItems: 'stretch' }}>
            <Stack flex={0} style={{ minWidth: '300px' }}>
              {event && (
                <DcFieldEventHeader
                  event={event}
                  eventStatus={eventStatus}
                  eventStartTime={eventStartTime}
                  eventEndTime={eventEndTime}
                />
              )}
              <DcFieldRootCauseSelection
                event={event}
                showAllCauses={showAllCauses}
                setShowAllCauses={setShowAllCauses}
                selectedRootCause={selectedRootCause}
                setSelectedRootCause={setSelectedRootCause}
                rootCauses={rootCauses}
                onRootCauseChange={(cause) => {
                  setSelectedRootCause(cause)
                  open()
                }}
              />
              <EventLosses losses={losses} />
            </Stack>
            <Stack flex={1} style={{ minHeight: '400px' }}>
              <DcFieldAnomaliesMap
                event={event ?? null}
                projectId={projectId || '-1'}
              />
            </Stack>
          </Group>
          <CustomCard title="Event Traces" fill style={{ height: '400px' }}>
            <PlotlyPlot
              isLoading={expectedPower.isLoading}
              xAxisTimeZone={projectTz}
              data={[
                { yaxis: 'y' }, // Yes, we need this. No, I don't know why.

                // Add expected power traces for DC combiner (main traces for DC Field events)
                ...(expectedPower.data && dcCombinerDevice
                  ? [
                      {
                        x: expectedPower.data.times,
                        y: expectedPower.data.actual.power,
                        name: 'Actual Power (DC Combiner)',
                        type: 'scatter' as const,
                        fill: 'tozeroy' as const,
                        fillcolor: 'rgba(0, 128, 0, 0.2)',
                        line: { color: theme.colors.green[7], width: 2 },
                        yaxis: 'y',
                      },
                      {
                        x: expectedPower.data.times,
                        y: expectedPower.data.expected_soiled.power,
                        name: 'Expected Power (Soiled)',
                        type: 'scatter' as const,
                        line: {
                          color: theme.colors.orange[6],
                          width: 2,
                        },
                        yaxis: 'y',
                      },
                      {
                        x: expectedPower.data.times,
                        y: powerDifferenceMovingAverage,
                        name: 'Power Difference (Soiled) - 20pt Moving Avg',
                        type: 'scatter' as const,
                        fill: 'tozeroy' as const,
                        fillcolor: 'rgba(255, 0, 0, 0.2)',
                        line: { color: theme.colors.red[6], width: 1 },
                        yaxis: 'y',
                      },
                    ]
                  : []),
              ]}
              layout={{
                shapes: [
                  {
                    type: 'rect',
                    x0: eventStartTime.format('YYYY-MM-DD HH:mm:ss'),
                    x1:
                      eventEndTime.isValid() && eventEndTime <= traceEnd
                        ? eventEndTime.format('YYYY-MM-DD HH:mm:ss')
                        : traceEnd.format('YYYY-MM-DD HH:mm:ss'),
                    y0: 0,
                    y1: 1,
                    xref: 'x',
                    yref: 'paper',
                    line: {
                      width: 0,
                    },
                  },
                ],
                // Y-axis configuration for power data
                yaxis: {
                  title: {
                    text: 'Power (kW)',
                  },
                  side: 'left',
                  showgrid: true,
                  zeroline: false,
                  automargin: true,
                },
                hoverlabel: {
                  namelength: -1,
                },
              }}
            />
          </CustomCard>
          {eventId > 0 && projectId && (
            <CustomCard
              allowFullscreen={false}
              title="Team Insights"
              style={{ height: '600px', flex: 1 }}
            >
              <EventChat eventId={eventId} projectId={projectId} />
            </CustomCard>
          )}
        </Stack>
        <Stack flex={0} style={{ minWidth: '350px' }}>
          <CustomCard
            allowFullscreen={false}
            title="Timeline"
            style={{ height: '600px', maxHeight: '600px' }}
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
    </>
  )
}

export default Page
