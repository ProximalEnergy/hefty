import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

type UtilityExpected = types.components['schemas']['UtilityExpectedResponse']

type UtilityExpectedOperation =
  'utility_expected_v1_protected__project_id__pv_expected_energy_plot_get'
type UtilityExpectedQueryParams =
  types.operations[UtilityExpectedOperation]['parameters']['query']

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
