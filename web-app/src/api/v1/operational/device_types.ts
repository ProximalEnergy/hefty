import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'DeviceType'
const URL = '/v1/operational/device-types'

export type DeviceType = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']

export const useGetDeviceTypes = ({
  queryParams = {},
  queryOptions = {},
}: {
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

  return useCustomQuery<DeviceType[]>({
    axiosConfig,
    queryName: 'getDeviceTypes',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
