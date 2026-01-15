import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _URL = '/v1/operational/projects/{project_id}/cmms-tickets' as const

type get = types.paths[typeof _URL]['get']
type getQueryParams = get['parameters']['query']
type getPathParams = get['parameters']['path']
type getResponse = get['responses'][200]['content']['application/json']

type CMMSResponse = getResponse
export type CMMSTicket = getResponse['data'][number]

export const useGetCMMSTickets = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: getPathParams['project_id'] }
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/cmms-tickets`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 5,
  }

  return useCustomQuery<CMMSResponse>({
    axiosConfig,
    queryName: 'getCMMSTickets',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
