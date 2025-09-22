import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface DeviceDetailsHorizontalPV {
  times: string[]
  met: {
    values: number[]
    name: string
    device_id: number
  }[]
  pcs: {
    values: number[]
    name: string
    device_id: number
  }[]
}

export const useGetDeviceDetailsHorizontalPV = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/device-details/horizontal/pv`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DeviceDetailsHorizontalPV>({
    axiosConfig,
    queryName: 'getDeviceDetailsHorizontalPV',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}
