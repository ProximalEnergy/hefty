import { components, paths } from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const URL = '/v1/operational/projects/{project_id}/issues'

type get = paths[typeof URL]['get']
type getPathParams = get['parameters']['path']
type getQueryParams = get['parameters']['query']

export type ProjectIssue = components['schemas']['ProjectIssueSummary']

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
