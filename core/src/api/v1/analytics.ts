import { UseQueryOptions } from '@tanstack/react-query'

import { useCustomQuery } from '../../hooks/api'
import { Device } from '../../hooks/types'

export interface UtilityExpected {
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
  }
}) => {
  const axiosConfig = {
    url: `/v1/protected/${pathParams.projectId}/pv-expected-energy`,
    params: queryParams,
  }
  const defaultQueryOptions: Partial<UseQueryOptions> = {
    staleTime: 5 * 60 * 1000,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<UtilityExpected>({
    axiosConfig,
    queryName: 'getUtilityExpected',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}
