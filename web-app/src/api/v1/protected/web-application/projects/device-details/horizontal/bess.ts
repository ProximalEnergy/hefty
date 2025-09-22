import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface DeviceDetailsHorizontalBESS {
  times: string[]
  pcs: {
    values: number[]
    name: string
    device_id: number
  }[]
  battery: {
    values: number[]
    name: string
    device_id: number
  }[]
}

export const useGetDeviceDetailsHorizontalBESS = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/device-details/horizontal/bess`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DeviceDetailsHorizontalBESS>({
    axiosConfig,
    queryName: 'getDeviceDetailsHorizontalBESS',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}
