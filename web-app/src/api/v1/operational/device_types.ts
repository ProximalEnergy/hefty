import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export interface DeviceType {
  device_type_id: number
  name_short: string
  name_long: string
}

export const useGetDeviceTypes = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/device-types/`,
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
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}
