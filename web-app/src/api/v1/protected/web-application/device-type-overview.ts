import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface DeviceTypePowerSummary {
  device_type_power: Record<number, number> // device_type_id -> power in MW
  timestamp: string // ISO timestamp of the data
}

export const useGetDeviceTypePowerSummary = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions<DeviceTypePowerSummary>>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/real-time/device-type-overview/power-summary`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 30 * 1000, // Cache for 30 seconds since this is real-time data
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  }

  const combinedQueryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DeviceTypePowerSummary>({
    axiosConfig,
    queryName: 'getDeviceTypePowerSummary',
    pathParams,
    queryOptions: combinedQueryOptions,
  })
}
