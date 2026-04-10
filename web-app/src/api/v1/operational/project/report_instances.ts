import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'ReportInstance'
const URL = '/v1/operational/projects/{project_id}/report-instances'

export type ReportInstance = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']
type getPathParams = get['parameters']['path']

export const useGetProjectReportInstances = ({
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

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<ReportInstance[]>({
    axiosConfig,
    queryName: 'getReportInstances',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
