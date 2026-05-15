import {
  type ProjectIssue,
  useGetProjectIssues,
} from '@/api/v1/operational/project/issues'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetSensorTypes } from '@/api/v1/operational/sensor_types'
import { DataTable } from '@/components/DataTable'
import { PageLoader } from '@/components/Loading'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { getQueryParamDateRange } from '@/components/datepicker/utils'
import { useGetTags } from '@/hooks/api'
import {
  Group,
  LoadingOverlay,
  MultiSelect,
  Stack,
  Switch,
  Text,
} from '@mantine/core'
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
import relativeTime from 'dayjs/plugin/relativeTime'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'

dayjs.extend(timezone)
dayjs.extend(relativeTime)
dayjs.extend(utc)

const formatIssueTableTime = (value: string | null, timeZone: string) => {
  return value !== null
    ? dayjs(value).tz(timeZone).format('MM/DD/YYYY HH:mm:ss')
    : ''
}

const formatIssueDuration = (timeStart: string, timeEnd: string | null) => {
  const endTime = timeEnd !== null ? dayjs(timeEnd) : dayjs()
  const durationHours = Math.max(0, endTime.diff(dayjs(timeStart), 'hour'))

  if (durationHours < 24) {
    return `${durationHours} ${durationHours === 1 ? 'hour' : 'hours'}`
  }

  const durationDays = Math.floor(durationHours / 24)

  return `${durationDays} ${durationDays === 1 ? 'day' : 'days'}`
}

const removePrefix = (value: string, prefix: string) => {
  return value.startsWith(prefix) ? value.slice(prefix.length).trim() : value
}

type ProjectIssueRow = ProjectIssue & {
  device_name_display: string
  issue_duration: string
  sensor_type_name_display: string
  sensor_type_name_long: string
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

const ProjectIssuesTable = ({
  data,
  timeZone,
}: {
  data: ProjectIssueRow[]
  timeZone: string
}) => {
  const table = useReactTable({
    data,
    columns: columns(timeZone),
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
      table={table}
    />
  )
}

const ProjectIssues = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const [selectedDeviceTypes, setSelectedDeviceTypes] = useState<string[]>([])
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
  const defaultIncludeClosedIssues = Boolean(
    selectedDateRangeKey && !selectedRangeIsToday,
  )
  const [closedIssuesState, setClosedIssuesState] = useState<{
    rangeKey: string | null
    value: boolean
  }>({ rangeKey: null, value: false })
  const includeClosedIssues =
    closedIssuesState.rangeKey === selectedDateRangeKey
      ? closedIssuesState.value
      : defaultIncludeClosedIssues
  const project = useSelectProject(projectId!)
  const issues = useGetProjectIssues({
    pathParams: { project_id: projectId as string },
    queryParams: {
      active_only: !includeClosedIssues,
      start: startQuery,
      end: endQuery,
    },
  })

  const deviceTypeOptions = useMemo(() => {
    const deviceTypesById = new Map<string, string>()

    for (const issue of issues.data ?? []) {
      if (issue.device_type_id !== null) {
        deviceTypesById.set(
          issue.device_type_id.toString(),
          issue.device_type_name,
        )
      }
    }

    return Array.from(deviceTypesById, ([value, label]) => ({
      value,
      label,
    }))
  }, [issues.data])

  const issueTagIds = useMemo(() => {
    return Array.from(
      new Set(
        (issues.data ?? [])
          .map((issue) => issue.tag_id)
          .filter((tagId): tagId is number => tagId !== null),
      ),
    )
  }, [issues.data])

  const issueTags = useGetTags({
    pathParams: { projectId: projectId as string },
    queryParams: { tag_ids: issueTagIds },
    queryOptions: {
      enabled: issueTagIds.length > 0,
    },
  })

  const issueSensorTypeIds = useMemo(() => {
    return Array.from(
      new Set(
        (issueTags.data ?? [])
          .map((tag) => tag.sensor_type_id)
          .filter((sensorTypeId): sensorTypeId is number => {
            return sensorTypeId !== null
          }),
      ),
    )
  }, [issueTags.data])

  const sensorTypes = useGetSensorTypes({
    queryParams: { sensor_type_ids: issueSensorTypeIds },
    queryOptions: {
      enabled: issueSensorTypeIds.length > 0,
    },
  })

  const issueRows = useMemo<ProjectIssueRow[]>(() => {
    const sensorTypeIdByTagId = new Map(
      (issueTags.data ?? []).map((tag) => [tag.tag_id, tag.sensor_type_id]),
    )
    const sensorTypeNameById = new Map(
      (sensorTypes.data ?? []).map((sensorType) => [
        sensorType.sensor_type_id,
        sensorType.name_long,
      ]),
    )

    return (issues.data ?? []).map((issue) => {
      const sensorTypeId =
        issue.tag_id !== null ? sensorTypeIdByTagId.get(issue.tag_id) : null

      const sensorTypeNameLong =
        sensorTypeId !== null && sensorTypeId !== undefined
          ? (sensorTypeNameById.get(sensorTypeId) ?? '')
          : ''

      return {
        ...issue,
        device_name_display: removePrefix(
          issue.device_name_full,
          issue.device_type_name,
        ),
        issue_duration: formatIssueDuration(issue.time_start, issue.time_end),
        sensor_type_name_display: removePrefix(
          sensorTypeNameLong,
          issue.device_type_name,
        ),
        sensor_type_name_long: sensorTypeNameLong,
      }
    })
  }, [issueTags.data, issues.data, sensorTypes.data])

  const filteredIssueRows = useMemo(() => {
    if (selectedDeviceTypes.length === 0) {
      return issueRows
    }

    return issueRows.filter((issue) => {
      return (
        issue.device_type_id !== null &&
        selectedDeviceTypes.includes(issue.device_type_id.toString())
      )
    })
  }, [issueRows, selectedDeviceTypes])

  const isIssueMetadataLoading =
    (issueTagIds.length > 0 && issueTags.isLoading) ||
    (issueSensorTypeIds.length > 0 && sensorTypes.isLoading)

  if (project.isLoading) {
    return <PageLoader />
  }

  return (
    <Stack>
      <Group justify="space-between">
        <Switch
          checked={includeClosedIssues}
          onChange={(event) =>
            setClosedIssuesState({
              rangeKey: selectedDateRangeKey,
              value: event.currentTarget.checked,
            })
          }
          label="Include Closed Issues"
        />
        <Group>
          <AdvancedDatePicker
            defaultRange="today"
            includeClearButton={false}
            includeIncrementButtons={false}
            includeTodayInDateRange={true}
          />
          <MultiSelect
            data={deviceTypeOptions}
            disabled={issues.isLoading}
            placeholder={
              selectedDeviceTypes.length == 0
                ? 'Select device types...'
                : undefined
            }
            value={selectedDeviceTypes}
            onChange={(value) => setSelectedDeviceTypes(value)}
            clearable
          />
        </Group>
      </Group>
      {issues.isLoading || isIssueMetadataLoading ? (
        <div style={{ position: 'relative', height: '250px', width: '100%' }}>
          <LoadingOverlay visible={true} />
        </div>
      ) : (
        <ProjectIssuesTable
          data={filteredIssueRows}
          timeZone={project.data?.time_zone ?? 'UTC'}
        />
      )}
    </Stack>
  )
}

export default ProjectIssues
