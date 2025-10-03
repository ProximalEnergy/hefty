import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export interface DeviceDetailsSingle {
  time: string[]
  data: {
    name: string
    values: number[]
    unit: string
  }[]
}

export const useGetDeviceDetailsSingle = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string; deviceId: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/device-details/single/${pathParams.deviceId}`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DeviceDetailsSingle>({
    axiosConfig,
    queryName: 'getDeviceDetailsSingle',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}
