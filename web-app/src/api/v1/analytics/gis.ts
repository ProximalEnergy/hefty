import { useCustomQuery } from '@/hooks/api'
import { Device } from '@/hooks/types'
// Assuming a base Device type exists
import { UseQueryOptions } from '@tanstack/react-query'

// Define the structure for the power data added by the endpoint
type PowerData = {
  times: string[] // ISO date strings
  actual: {
    power: (number | null)[]
  }
  expected_soiled: {
    power: (number | null)[]
    unique_versions: string[]
    // difference removed as per previous request
  }
} | null // It can be null if not requested or not found

// Extend the base Device type to include optional power_data
type DeviceWithPower = Device & {
  power_data: PowerData
  tracker_data?: {
    // Add optional tracker data
    tracker_angle: number | null
  } | null
  met_station_values?: {
    poa: number | null
    ghi: number | null
    ambient_temp: number | null
    wind_speed: number | null
  } | null
}

// Type for the hook's query parameters
type DevicesInViewportQueryParams = {
  north: number
  east: number
  south: number
  west: number
  device_type_ids?: number[]
  power_device_type_id?: number
}

export const useGetDevicesInViewport = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  // Project ID is needed for context, even if not in URL path itself.
  pathParams: { projectId: string }
  queryParams: DevicesInViewportQueryParams
  // Expecting an array.
  queryOptions?: Partial<UseQueryOptions<DeviceWithPower[]>>
}) => {
  const axiosConfig = {
    // We pass projectId contextually but it's not part of this specific URL path
    // The project context is likely handled by backend dependencies via headers/auth.
    // Update URL to include projectId based on Swagger example
    url: `/v1/gis/${pathParams.projectId}/devices-in-viewport`,
  }

  // Default options - adjust staleTime/refetch as needed for viewport data
  const defaultQueryOptions: Partial<UseQueryOptions<DeviceWithPower[]>> = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // Cache viewport data for 5 minutes?
  }

  const combinedQueryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<DeviceWithPower[]>({
    axiosConfig,
    queryName: 'getDevicesInViewport',
    pathParams,
    queryParams,
    queryOptions: combinedQueryOptions,
  })
}
