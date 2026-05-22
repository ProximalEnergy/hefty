import {
  type ProjectIssue,
  useGetIssueDevices,
  useGetProjectIssues,
} from '@/api/v1/operational/project/issues'
import { useGetSensorTypes } from '@/api/v1/operational/sensor_types'
import { getQueryParamDateRange } from '@/components/datepicker/utils'
import { useGetTags } from '@/hooks/api'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import type { ProjectImpactsContext } from '@/features/project-impacts/types/project-impacts-types'

dayjs.extend(timezone)
dayjs.extend(utc)

type ProjectImpactsIssuesViewModelProps = {
  context: ProjectImpactsContext
}

export type ProjectIssueRow = ProjectIssue & {
  device_name_display: string
  issue_duration: string
  sensor_type_name_display: string
  sensor_type_name_long: string
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

export function useProjectImpactsIssuesViewModel({
  context,
}: ProjectImpactsIssuesViewModelProps) {
  const [selectedDevices, setSelectedDevices] = useState<string[]>([])
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

  const issues = useGetProjectIssues({
    pathParams: { project_id: context.projectId },
    queryParams: {
      active_only: !includeClosedIssues,
      device_ids: selectedDevices.map((device) => parseInt(device)),
      start: startQuery,
      end: endQuery,
    },
  })

  const issueDevices = useGetIssueDevices({
    pathParams: { project_id: context.projectId },
  })

  const deviceTypeOptions = useMemo(() => {
    return (issueDevices.data?.unique_types ?? []).map((deviceType) => ({
      value: deviceType.device_type_id.toString(),
      label: deviceType.device_type_name,
    }))
  }, [issueDevices.data])

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
    pathParams: { projectId: context.projectId },
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

  return {
    deviceTypeOptions,
    filteredIssueRows,
    includeClosedIssues,
    isLoading: issues.isLoading || isIssueMetadataLoading,
    issuesError:
      issues.error ??
      issueTags.error ??
      sensorTypes.error ??
      issueDevices.error ??
      null,
    issueDevices,
    projectId: context.projectId,
    selectedDateRangeKey,
    selectedDevices,
    selectedDeviceTypes,
    setClosedIssuesState,
    setSelectedDevices,
    setSelectedDeviceTypes,
    timeZone: context.project?.time_zone ?? 'UTC',
  }
}
