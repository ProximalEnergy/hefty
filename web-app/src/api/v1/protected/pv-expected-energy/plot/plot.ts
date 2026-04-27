import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

type UtilityExpected = types.components['schemas']['UtilityExpectedResponse']

type UtilityExpectedPath = '/v1/protected/{project_id}/pv-expected-energy/plot'
type UtilityExpectedQueryParams =
  types.paths[UtilityExpectedPath]['get']['parameters']['query']

export const useGetUtilityExpected = ({
  pathParams,
  queryOptions = {},
  queryParams = { device_id: -1, start: '', end: '' },
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
  queryParams?: UtilityExpectedQueryParams
}) => {
  const axiosConfig = {
    url: `/v1/protected/${pathParams.projectId}/pv-expected-energy/plot`,
  }
  const defaultQueryOptions = {
    staleTime: QUERY_TIME.FIVE_MINUTES,
  }

  return useCustomQuery<UtilityExpected>({
    axiosConfig,
    queryName: 'getUtilityExpected',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
