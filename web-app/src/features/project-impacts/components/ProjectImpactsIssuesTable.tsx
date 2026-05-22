import { DataTable } from '@/components/DataTable/DataTable'
import { Text } from '@mantine/core'
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
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import type { ProjectIssueRow } from '@/features/project-impacts/hooks/use-project-impacts-issues-view-model'
import { ProjectImpactsIssueTimeSeriesPlot } from '@/features/project-impacts/components/ProjectImpactsIssueTimeSeriesPlot'

dayjs.extend(timezone)
dayjs.extend(utc)

const formatIssueTableTime = (value: string | null, timeZone: string) => {
  return value !== null
    ? dayjs(value).tz(timeZone).format('MM/DD/YYYY HH:mm:ss')
    : ''
}

const columnHelper = createColumnHelper<ProjectIssueRow>()
const emptyAggregatedCell = () => null

const columns = (timeZone: string) => [
  columnHelper.accessor('issue_category', {
    aggregatedCell: emptyAggregatedCell,
    header: 'Category',
  }),
  columnHelper.accessor('device_type_name', {
    aggregatedCell: emptyAggregatedCell,
    header: 'Device Type',
  }),
  columnHelper.accessor('device_name_display', {
    aggregatedCell: emptyAggregatedCell,
    header: 'Device',
  }),
  columnHelper.accessor('sensor_type_name_display', {
    aggregatedCell: emptyAggregatedCell,
    header: 'Sensor Type',
  }),
  columnHelper.accessor('time_start', {
    aggregatedCell: emptyAggregatedCell,
    header: 'Start Time',
    cell: (props) => (
      <Text>
        {formatIssueTableTime(props.cell.getValue<string | null>(), timeZone)}
      </Text>
    ),
  }),
  columnHelper.accessor('time_end', {
    aggregatedCell: emptyAggregatedCell,
    header: 'End Time',
    cell: (props) => (
      <Text>
        {formatIssueTableTime(props.cell.getValue<string | null>(), timeZone)}
      </Text>
    ),
  }),
  columnHelper.accessor('issue_duration', {
    aggregatedCell: emptyAggregatedCell,
    header: 'Duration',
  }),
]

type ProjectImpactsIssuesTableProps = {
  data: ProjectIssueRow[]
  projectId: string
  timeZone: string
}

export function ProjectImpactsIssuesTable({
  data,
  projectId,
  timeZone,
}: ProjectImpactsIssuesTableProps) {
  const table = useReactTable({
    data,
    columns: columns(timeZone),
    getRowCanExpand: (row) =>
      row.getIsGrouped() || row.original.tag_id !== null,
    getRowId: (row) => row.issue_id.toString(),
    initialState: {
      grouping: ['issue_category'],
      sorting: [{ id: 'time_start', desc: true }],
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getGroupedRowModel: getGroupedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  return (
    <DataTable
      emptyState={
        <Text c="dimmed" size="sm">
          No issues
        </Text>
      }
      getRowCanClick={(row) => row.original.tag_id !== null}
      onRowClick={(row) => row.toggleExpanded()}
      renderExpandedRow={(row) => (
        <ProjectImpactsIssueTimeSeriesPlot
          issue={row.original}
          projectId={projectId}
          timeZone={timeZone}
        />
      )}
      table={table}
    />
  )
}
