import { paths } from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const URL = '/v1/operational/projects/{project_id}/issues'

type get = paths[typeof URL]['get']
type getPathParams = get['parameters']['path']
type getQueryParams = get['parameters']['query']

export interface ProjectIssue {
  issue_id: number
  device_id: number
  device_type_id: number | null
  device_type_name: string
  device_name_full: string
  tag_id: number | null
  issue_category_id: number
  issue_category: string
  time_start: string
  time_end: string | null
}

export const useGetProjectIssues = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: getPathParams
  queryParams?: getQueryParams
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
