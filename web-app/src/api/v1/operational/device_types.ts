import * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const COMPONENT_NAME = 'DeviceType'
const URL = '/v1/operational/device-types/'

type DeviceType = types.components['schemas'][typeof COMPONENT_NAME]
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
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DeviceType[]>({
    axiosConfig,
    queryName: 'getDeviceTypes',
    pathParams: {},
    queryParams,
    queryOptions,
  })
}
