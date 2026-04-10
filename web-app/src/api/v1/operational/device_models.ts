import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'DeviceModel'
const URL = '/v1/operational/device-models'

type DeviceModel = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']

export const useGetDeviceModels = ({
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
    staleTime: QUERY_TIME.FIVE_MINUTES, // 5 minutes
  }

  return useCustomQuery<DeviceModel[]>({
    axiosConfig,
    queryName: 'getDeviceModels',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
