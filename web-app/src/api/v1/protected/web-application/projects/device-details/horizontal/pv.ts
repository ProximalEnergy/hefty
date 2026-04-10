import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'DeviceDetailsHorizontalPV'
const URL =
  '/v1/protected/web-application/projects/{project_id}/device-details/horizontal/pv'

type DeviceDetailsHorizontalPV =
  types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']
type getPathParams = get['parameters']['path']

export const useGetDeviceDetailsHorizontalPV = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: getPathParams
  queryParams: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {
    staleTime: QUERY_TIME.FIVE_MINUTES,
    refetchOnWindowFocus: false,
  }

  return useCustomQuery<DeviceDetailsHorizontalPV>({
    axiosConfig,
    queryName: 'getDeviceDetailsHorizontalPV',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
