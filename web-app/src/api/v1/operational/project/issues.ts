import { components, paths } from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import type { EventDeviceInfo } from '@/hooks/types'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const URL = '/v1/operational/projects/{project_id}/issues'
const ISSUE_DEVICES_URL =
  '/v1/operational/projects/{project_id}/issues/issue-devices'

type get = paths[typeof URL]['get']
type getPathParams = get['parameters']['path']
type getQueryParams = get['parameters']['query']
type ProjectIssuesQueryParams = getQueryParams & {
  device_ids?: number[]
}

export type ProjectIssue = components['schemas']['ProjectIssueSummary']

export const useGetProjectIssues = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: getPathParams
  queryParams?: ProjectIssuesQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  return useCustomQuery<ProjectIssue[]>({
    axiosConfig,
    queryName: 'getProjectIssues',
    pathParams,
    queryParams,
    queryOptions,
  })
}

export const useGetIssueDevices = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: getPathParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: ISSUE_DEVICES_URL,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<EventDeviceInfo>({
    axiosConfig,
    queryName: 'getIssueDevices',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
