import { DeviceDetailsHorizontalData } from '@/api/v1/protected/web-application/projects/device-details/horizontal/horizontal'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface DeviceDetailsHorizontalBESS {
  times: string[]
  meter_power: DeviceDetailsHorizontalData[]
  meter_soc: DeviceDetailsHorizontalData[]
  pcs: DeviceDetailsHorizontalData[]
  battery: DeviceDetailsHorizontalData[]
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
