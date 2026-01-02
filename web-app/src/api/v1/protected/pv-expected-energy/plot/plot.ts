import { useCustomQuery } from '@/hooks/api'
import { Device, MeterPowerAndExpected } from '@/hooks/types'
import { UseQueryOptions } from '@tanstack/react-query'

interface UtilityExpected {
  parent_devices: Device[]
  times: string[]
  actual: {
    power: number[]
  }
  expected_clean: {
    power: number[]
    version: string[]
    unique_versions: string[]
    difference: number[]
  }
  expected_soiled: {
    power: number[]
    version: string[]
    unique_versions: string[]
    difference: number[]
  }
  poa: {
    [key: string]: number[]
  }
  soiling: {
    [key: string]: number[]
  }
}

export const useGetUtilityExpected = ({
  pathParams,
  queryOptions = {},
  queryParams = { device_id: -1, start: '', end: '' },
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
  queryParams?: {
    device_id: number
    start: string
    end: string
    warranted_degradation?: boolean
  }
}) => {
  const axiosConfig = {
    url: `/v1/protected/${pathParams.projectId}/pv-expected-energy/plot`,
  }
  const defaultQueryOptions: Partial<UseQueryOptions> = {
    staleTime: 5 * 60 * 1000,
  }

  return useCustomQuery<UtilityExpected>({
    axiosConfig,
    queryName: 'getUtilityExpected',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetMeterPowerAndExpectedPower = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    include_storage?: boolean
    start?: string // Add start parameter type
    end?: string // Add end parameter type
    include_setpoint?: boolean // Add this parameter
    interval?: string
    include_soiling?: boolean
    include_degradation?: boolean
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/system/${pathParams.projectId}/meter-power-and-expected-power-v2`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    // Add appropriate defaults if needed, e.g., refetchOnWindowFocus
    refetchOnWindowFocus: false,
  }

  // Ensure the return type matches what the hook expects
  // Assuming it's still types.MeterPowerAndExpected
  return useCustomQuery<MeterPowerAndExpected>({
    axiosConfig,
    queryName: 'getMeterPowerAndExpectedPower',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
