import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { MeterPowerAndExpected } from '@/hooks/types'
import { UseQueryOptions } from '@tanstack/react-query'

type UtilityExpected = types.components['schemas']['UtilityExpectedResponse']

type UtilityExpectedOperation =
  'utility_expected_v1_protected__project_id__pv_expected_energy_plot_get'
type UtilityExpectedQueryParams =
  types.operations[UtilityExpectedOperation]['parameters']['query']

type MeterPowerQueryParams = {
  start?: string | null
  end?: string | null
  include_storage?: boolean
  include_setpoint?: boolean
  include_soiling?: boolean
  include_degradation?: boolean
  interval?: string
  schema?: string | null
}

export const useGetUtilityExpected = ({
  pathParams,
  queryOptions = {},
  queryParams = { device_id: -1, start: '', end: '' },
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
  queryParams?: UtilityExpectedQueryParams
}) => {
  const axiosConfig = {
    url: `/v1/protected/${pathParams.projectId}/pv-expected-energy/plot`,
  }
  const defaultQueryOptions = {
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
  queryParams?: MeterPowerQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url:
      `/v1/protected/system/${pathParams.projectId}` +
      '/meter-power-and-expected-power-v2',
  }

  const defaultQueryOptions = {
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
