import { ProjectTypeEnum } from '@/api/enumerations'
import {
  useGetEventDevices,
  useGetEventsSummary,
} from '@/api/v1/operational/project/events'
import { type Project, useSelectProject } from '@/api/v1/operational/projects'
import { DataTable } from '@/components/DataTable'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { useTipsEventsTable } from '@/components/Tips'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { getQueryParamDateRange } from '@/components/datepicker/utils'
import { useProjectFilter } from '@/hooks/custom'
import { EventSummary } from '@/hooks/types'
import ProjectEventsMap from '@/pages/projects/events/ProjectEventsMap'
import {
  ActionIcon,
  Group,
  LoadingOverlay,
  MultiSelect,
  Stack,
  Switch,
  Text,
} from '@mantine/core'
import { IconExternalLink } from '@tabler/icons-react'
import {
  createColumnHelper,
  getCoreRowModel,
  getExpandedRowModel,
  getFilteredRowModel,
  getGroupedRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import dayjs from 'dayjs'
import {
  default as relativeTime,
  default as utc,
} from 'dayjs/plugin/relativeTime'
import timezone from 'dayjs/plugin/timezone'
import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router'

dayjs.extend(timezone)
dayjs.extend(relativeTime)
dayjs.extend(utc)

const ProjectEvents = ({
  withPageTitle = true,
}: {
  withPageTitle?: boolean
}) => {
  // Hooks
  useTipsEventsTable()
  useProjectFilter({
    hasEventIntegration: true,
  })

  // Local State
  const [selectedDevices, setSelectedDevices] = useState<string[]>([])
  const [selectedDeviceTypes, setSelectedDeviceTypes] = useState<string[]>([])

  // URL State
  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams] = useSearchParams()
  const { start, end, startQuery, endQuery } = getQueryParamDateRange({
    searchParams,
    maxDays: 30,
    format: 'YYYY-MM-DD HH:mm:ss',
  })
  const selectedDateRangeKey =
    start && end
      ? `${start.format('YYYY-MM-DD')}:${end.format('YYYY-MM-DD')}`
      : null
  const selectedRangeIsToday = Boolean(
    start && end && start.isSame(dayjs(), 'day') && end.isSame(dayjs(), 'day'),
  )
  const defaultShowClosedEvents = Boolean(
    selectedDateRangeKey && !selectedRangeIsToday,
  )
  const [closedEventsState, setClosedEventsState] = useState<{
    rangeKey: string | null
    value: boolean
  }>({ rangeKey: null, value: false })
  const showClosedEvents =
    closedEventsState.rangeKey === selectedDateRangeKey
      ? closedEventsState.value
      : defaultShowClosedEvents
  // Data Fetching
  const eventDevices = useGetEventDevices({
    pathParams: { projectId: projectId as string },
  })
  const isEventDevicesLoading = eventDevices.isLoading
  const eventsSummary = useGetEventsSummary({
    pathParams: { projectId: projectId as string },
    queryParams: {
      start: startQuery,
      end: endQuery,
      device_type_ids: selectedDeviceTypes.map((type) => parseInt(type)),
      device_ids: selectedDevices.map((device) => parseInt(device)),
      open: !showClosedEvents,
    },
  })
  const project = useSelectProject(projectId!)

  if (project.isLoading) {
    return <PageLoader />
  }

  return (
    <Stack p={withPageTitle ? 'md' : 0}>
      {withPageTitle && (
        <PageTitle
          info={
            'This page displays a summary of project events. Use the filters ' +
            'to narrow down the events displayed in the table.'
          }
        >
          Events
        </PageTitle>
      )}
      <Group justify="space-between">
        <Switch
          checked={showClosedEvents}
          onChange={(event) =>
            setClosedEventsState({
              rangeKey: selectedDateRangeKey,
              value: event.currentTarget.checked,
            })
          }
          label="Include Closed Events"
        />
        <Group>
          <AdvancedDatePicker
            defaultRange="today"
            includeClearButton={false}
            includeIncrementButtons={false}
            includeTodayInDateRange={true}
          />
          <MultiSelect
            data={eventDevices.data?.unique_types.map((type) => ({
              value: type.device_type_id.toString(),
              label: type.device_type_name,
            }))}
            disabled={isEventDevicesLoading}
            placeholder={
              selectedDeviceTypes.length == 0
                ? 'Select device types...'
                : undefined
            }
            value={selectedDeviceTypes}
            onChange={(value) => setSelectedDeviceTypes(value)}
            clearable
          />
          <MultiSelect
            data={eventDevices.data?.unique_devices.map((device) => ({
              value: device.device_id.toString(),
              label: device.device_name_full,
            }))}
            disabled={isEventDevicesLoading}
            placeholder={
              selectedDevices.length == 0 ? 'Search devices...' : undefined
            }
            value={selectedDevices}
            onChange={(value) => setSelectedDevices(value)}
            clearable
            searchable
            limit={50}
          />
        </Group>
      </Group>
      {eventsSummary.isLoading ? (
        <div style={{ position: 'relative', height: '250px', width: '100%' }}>
          <LoadingOverlay visible={true} />
        </div>
      ) : (
        project.data && (
          <Stack>
            <EventTable
              data={eventsSummary.data ?? []}
              project={project.data}
            />
            <ProjectEventsMap
              events={eventsSummary.data ?? []}
              project={project.data}
            />
          </Stack>
        )
      )}
    </Stack>
  )
}

const columnHelper = createColumnHelper<EventSummary>()

const formatEventTableCurrency = (value: number | null) => {
  return value !== null && value !== 0
    ? value.toLocaleString('en-US', {
        style: 'currency',
        currency: 'USD',
      })
    : ''
}

const formatEventTableTime = (value: string | null, timeZone: string) => {
  return value !== null
    ? dayjs(value).tz(timeZone).format('MM/DD/YYYY HH:mm:ss')
    : ''
}

const formatEventTableEnergy = (value: number | null) => {
  return value !== null && value !== 0
    ? value.toLocaleString('en-US', {
        style: 'decimal',
        maximumFractionDigits: 2,
        minimumFractionDigits: 2,
      }) + ' MWh'
    : ''
}

const columns = (project: Project) => {
  return [
    columnHelper.display({
      id: 'actions',
      header: '',
      size: 48,
      cell: (props) => (
        <ActionIcon
          variant="transparent"
          onClick={() => {
            window.open(
              `${window.location.origin}/projects/${project.project_id}/events/event/?eventId=${props.cell.row.original.event_id}`,
            )
          }}
        >
          <IconExternalLink />
        </ActionIcon>
      ),
    }),
    columnHelper.accessor('device_type_name', { header: 'Device Type' }),
    columnHelper.accessor('device_name_full', { header: 'Device' }),
    columnHelper.accessor('loss_daily_financial', {
      header: 'Daily Loss ($)',
      aggregationFn: 'sum',
      cell: (props) => (
        <Text>
          {formatEventTableCurrency(props.cell.getValue<number | null>())}
        </Text>
      ),
      aggregatedCell: (props) => (
        <Text>
          {formatEventTableCurrency(props.cell.getValue<number | null>())}
        </Text>
      ),
    }),
    columnHelper.accessor('loss_total_financial', {
      header: 'Total Loss ($)',
      aggregationFn: 'sum',
      cell: (props) => (
        <Text>
          {formatEventTableCurrency(props.cell.getValue<number | null>())}
        </Text>
      ),
      aggregatedCell: (props) => (
        <Text>
          {formatEventTableCurrency(props.cell.getValue<number | null>())}
        </Text>
      ),
    }),
    columnHelper.accessor('time_start', {
      header: 'Start Time',
      cell: (props) => (
        <Text>
          {formatEventTableTime(
            props.cell.getValue<string | null>(),
            project.time_zone,
          )}
        </Text>
      ),
    }),
    columnHelper.accessor('time_end', {
      header: 'End Time',
      cell: (props) => (
        <Text>
          {formatEventTableTime(
            props.cell.getValue<string | null>(),
            project.time_zone,
          )}
        </Text>
      ),
    }),
    columnHelper.accessor('failure_mode', { header: 'Failure Mode' }),
    columnHelper.accessor('root_cause', { header: 'Root Cause' }),
    columnHelper.accessor('loss_total_energy', {
      header: 'Total Loss (MWh)',
      aggregationFn: 'sum',
      cell: (props) => (
        <Text>
          {formatEventTableEnergy(props.cell.getValue<number | null>())}
        </Text>
      ),
      aggregatedCell: (props) => (
        <Text>
          {formatEventTableEnergy(props.cell.getValue<number | null>())}
        </Text>
      ),
    }),
    columnHelper.accessor('loss_daily_energy', {
      header: 'Daily Loss (MWh)',
      aggregationFn: 'sum',
      cell: (props) => (
        <Text>
          {formatEventTableEnergy(props.cell.getValue<number | null>())}
        </Text>
      ),
      aggregatedCell: (props) => (
        <Text>
          {formatEventTableEnergy(props.cell.getValue<number | null>())}
        </Text>
      ),
    }),
  ]
}

export const EventTable = ({
  data,
  project,
}: {
  data: EventSummary[]
  project: Project
}) => {
  const showLosses = Boolean(
    project.project_type_id === ProjectTypeEnum.BESS ||
    project.has_expected_energy_integration,
  )

  const table = useReactTable({
    data,
    columns: columns(project),
    initialState: {
      grouping: ['device_type_name'],
      sorting: showLosses
        ? [{ id: 'loss_daily_financial', desc: true }]
        : [{ id: 'time_start', desc: true }],
      columnVisibility: {
        loss_daily_financial: showLosses,
        loss_total_financial: showLosses,
        loss_daily_energy: showLosses,
        loss_total_energy: showLosses,
      },
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getGroupedRowModel: getGroupedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  return <DataTable table={table} />
}

export default ProjectEvents
