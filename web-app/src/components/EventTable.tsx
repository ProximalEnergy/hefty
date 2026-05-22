import { ProjectTypeEnum } from '@/api/enumerations'
import { Project } from '@/api/v1/operational/projects'
import { DataTable } from '@/components/DataTable/DataTable'
import { EventSummary } from '@/hooks/types'
import { ActionIcon, Box, Text } from '@mantine/core'
import { IconExternalLink } from '@tabler/icons-react'
import {
  getFilteredRowModel,
  getExpandedRowModel,
  getGroupedRowModel,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  createColumnHelper,
} from '@tanstack/react-table'
import dayjs from 'dayjs'
import { useNavigate } from 'react-router'

export const EventTable = ({
  data,
  height,
  project,
}: {
  data: EventSummary[]
  height?: number | string
  project: Project
}) => {
  const navigate = useNavigate()
  const showLosses = Boolean(
    project.project_type_id === ProjectTypeEnum.BESS ||
    project.has_expected_energy_integration,
  )
  const openEvent = (eventId: number) => {
    navigate(
      `/projects/${project.project_id}/impacts/event/?eventId=${eventId}`,
    )
  }
  const openEventInNewWindow = (eventId: number) => {
    window.open(
      `${window.location.origin}/projects/${project.project_id}/impacts/event/?eventId=${eventId}`,
    )
  }

  const table = useReactTable({
    data,
    columns: EventTableColumns(project, openEventInNewWindow),
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

  return (
    <Box h={height} mih={0}>
      <DataTable
        getRowCanClick={(row) => !row.getIsGrouped()}
        onRowClick={(row) => openEvent(row.original.event_id)}
        table={table}
      />
    </Box>
  )
}

// Helpers & Factories
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

const EventTableColumns = (
  project: Project,
  openEventInNewWindow: (eventId: number) => void,
) => {
  return [
    columnHelper.display({
      id: 'actions',
      header: '',
      size: 48,
      cell: (props) => (
        <ActionIcon
          aria-label="Open event"
          variant="transparent"
          onClick={(event) => {
            event.stopPropagation()
            openEventInNewWindow(props.cell.row.original.event_id)
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
