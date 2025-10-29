import {
  useGetEventDevices,
  useGetEventsSummary,
} from '@/api/v1/operational/project/events'
import { useGetProject } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { useTipsEventsTable } from '@/components/Tips'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import { useProjectFilter } from '@/hooks/custom'
import { EventSummary } from '@/hooks/types'
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
import dayjs from 'dayjs'
import {
  default as relativeTime,
  default as utc,
} from 'dayjs/plugin/relativeTime'
import timezone from 'dayjs/plugin/timezone'
import {
  type MRT_Cell,
  MRT_ColumnDef,
  MantineReactTable,
  useMantineReactTable,
} from 'mantine-react-table'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

dayjs.extend(timezone)
dayjs.extend(relativeTime)
dayjs.extend(utc)

const ProjectEvents = () => {
  useTipsEventsTable()

  useProjectFilter({
    hasEventIntegration: true,
  })

  const { projectId } = useParams()

  const [selectedDeviceTypes, setSelectedDeviceTypes] = useState<string[]>([])
  const [selectedDevices, setSelectedDevices] = useState<string[]>([])
  const [showClosedEvents, setShowClosedEvents] = useState(false)
  const [navigateType, setNavigateType] = useState<'newTab' | 'navigate'>(
    'navigate',
  )
  const navigate = useNavigate()

  const { start: urlStart, end: urlEnd } = useValidateDateRange({
    maxDays: 30, // Limit to 30 days max
  })
  const startQuery = urlStart?.format('YYYY-MM-DD HH:mm:ss')
  const endQuery = urlEnd?.format('YYYY-MM-DD HH:mm:ss')

  const { data: project, isLoading: isProjectLoading } = useGetProject({
    pathParams: { projectId: projectId as string },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  const { data: eventDevices, isLoading: isEventDevicesLoading } =
    useGetEventDevices({
      pathParams: { projectId: projectId as string },
    })
  const { data: events, isLoading: isEventsLoading } = useGetEventsSummary({
    pathParams: { projectId: projectId as string },
    queryParams: {
      start: startQuery,
      end: endQuery,
      device_type_ids: selectedDeviceTypes.map((type) => parseInt(type)),
      device_ids: selectedDevices.map((device) => parseInt(device)),
      open: !showClosedEvents,
    },
    queryOptions: {
      enabled: true,
    },
  })

  const isLoading = isEventDevicesLoading || isProjectLoading

  const columns = useMemo(
    () => [
      {
        header: '',
        accessorKey: 'actions',
        enableSorting: false,
        enableColumnFilter: false,
        enableColumnActions: false,
        size: 24,
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <ActionIcon
            onMouseEnter={() => {
              setNavigateType('newTab')
            }}
            onMouseLeave={() => {
              setNavigateType('navigate')
            }}
            variant="transparent"
            onClick={() => {
              window.open(
                `${window.location.origin}/projects/${projectId}/events/event/?eventId=${cell.row.original.event_id}`,
              )
            }}
          >
            <IconExternalLink />
          </ActionIcon>
        ),
      },
      {
        header: 'Device Type',
        accessorKey: 'device_type_name',
      },
      {
        header: 'Device',
        accessorKey: 'device_name_full',
      },
      {
        header: 'Daily Loss ($)',
        accessorKey: 'loss_daily_financial',
        aggregationFn: 'sum',
        mantineTableHeadCellProps: {
          align: 'right',
        },
        mantineTableBodyCellProps: {
          align: 'right',
        },
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null
              ? cell.getValue<number>().toLocaleString('en-US', {
                  style: 'currency',
                  currency: 'USD',
                })
              : ''}
          </Text>
        ),
        AggregatedCell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null &&
            cell.getValue<number>() !== 0
              ? cell.getValue<number>().toLocaleString('en-US', {
                  style: 'currency',
                  currency: 'USD',
                })
              : ''}
          </Text>
        ),
      },
      {
        header: 'Total Loss ($)',
        accessorKey: 'loss_total_financial',
        aggregationFn: 'sum',
        mantineTableHeadCellProps: {
          align: 'right',
        },
        mantineTableBodyCellProps: {
          align: 'right',
        },
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null
              ? cell.getValue<number>().toLocaleString('en-US', {
                  style: 'currency',
                  currency: 'USD',
                })
              : ''}
          </Text>
        ),
        AggregatedCell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null &&
            cell.getValue<number>() !== 0
              ? cell.getValue<number>().toLocaleString('en-US', {
                  style: 'currency',
                  currency: 'USD',
                })
              : ''}
          </Text>
        ),
      },
      {
        header: 'Start Time',
        accessorKey: 'time_start',
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {dayjs(cell.getValue<string>())
              .tz(project?.time_zone)
              .format('MM/DD/YYYY HH:mm:ss')}
          </Text>
        ),
      },
      {
        header: 'End Time',
        accessorKey: 'time_end',
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<string | null>() !== null
              ? dayjs(cell.getValue<string>())
                  .tz(project?.time_zone)
                  .format('MM/DD/YYYY HH:mm:ss')
              : ''}
          </Text>
        ),
      },
      {
        header: 'Failure Mode',
        accessorKey: 'failure_mode',
      },
      {
        header: 'Root Cause',
        accessorKey: 'root_cause',
      },
      {
        header: 'Total Loss (MWh)',
        accessorKey: 'loss_total_energy',
        aggregationFn: 'sum',
        mantineTableHeadCellProps: {
          align: 'right',
        },
        mantineTableBodyCellProps: {
          align: 'right',
        },
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null
              ? `${cell.getValue<number>().toLocaleString('en-US', {
                  style: 'decimal',
                  maximumFractionDigits: 2,
                  minimumFractionDigits: 2,
                })} MWh`
              : ''}
          </Text>
        ),
        AggregatedCell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null &&
            cell.getValue<number>() !== 0
              ? `${cell.getValue<number>().toLocaleString('en-US', {
                  style: 'decimal',
                  maximumFractionDigits: 2,
                  minimumFractionDigits: 2,
                })} MWh`
              : ''}
          </Text>
        ),
      },
      {
        header: 'Daily Loss (MWh)',
        accessorKey: 'loss_daily_energy',
        aggregationFn: 'sum',
        mantineTableHeadCellProps: {
          align: 'right',
        },
        mantineTableBodyCellProps: {
          align: 'right',
        },
        Cell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null
              ? `${cell.getValue<number>().toLocaleString('en-US', {
                  style: 'decimal',
                  maximumFractionDigits: 2,
                  minimumFractionDigits: 2,
                })} MWh`
              : ''}
          </Text>
        ),
        AggregatedCell: ({ cell }: { cell: MRT_Cell<EventSummary> }) => (
          <Text size="sm">
            {cell.getValue<number | null>() !== null &&
            cell.getValue<number>() !== 0
              ? `${cell.getValue<number>().toLocaleString('en-US', {
                  style: 'decimal',
                  maximumFractionDigits: 2,
                  minimumFractionDigits: 2,
                })} MWh`
              : ''}
          </Text>
        ),
      },
    ],
    [project?.time_zone],
  )
  const table = useMantineReactTable({
    columns: columns as MRT_ColumnDef<EventSummary>[],
    data: events ?? [],
    enableGrouping: true,
    enableColumnDragging: false,
    initialState: {
      density: 'xs',
      grouping: ['device_type_name'],
      columnVisibility: {
        loss_total_financial: false,
        loss_total_energy: false,
        loss_daily_energy: false,
      },
      sorting: [{ id: 'loss_daily_financial', desc: true }],
    },
    mantineTableBodyRowProps: ({ row }) => ({
      onClick: () => {
        if (row.subRows?.length == 0 && navigateType == 'navigate') {
          navigate(
            `/projects/${projectId}/events/event/?eventId=${row.original.event_id}`,
          )
        }
      },
      style: {
        cursor: row.subRows?.length == 0 ? 'pointer' : 'default',
      },
    }),
  })

  if (isLoading) {
    return <PageLoader />
  }
  return (
    <Stack w="100%" p="md">
      <PageTitle
        info={
          <Text>
            This page displays a summary of project events. Use the filters to
            narrow down the events displayed in the table.
          </Text>
        }
      >
        Events
      </PageTitle>
      <Group justify="space-between">
        <Group>
          <Switch
            checked={showClosedEvents}
            onChange={(event) =>
              setShowClosedEvents(event.currentTarget.checked)
            }
            label="Include Closed Events"
          />
        </Group>
        <Group>
          <AdvancedDatePicker
            defaultRange="today"
            includeClearButton={false}
            includeIncrementButtons={false}
            includeTodayInDateRange={true}
          />
          <MultiSelect
            data={eventDevices?.unique_types.map((type) => ({
              value: type.device_type_id.toString(),
              label: type.device_type_name,
            }))}
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
            data={eventDevices?.unique_devices.map((device) => ({
              value: device.device_id.toString(),
              label: device.device_name_full,
            }))}
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
      <div style={{ position: 'relative', height: '100%', width: '100%' }}>
        <LoadingOverlay visible={isEventsLoading} />
        <MantineReactTable table={table} />
      </div>
    </Stack>
  )
}

export default ProjectEvents
