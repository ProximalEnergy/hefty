import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'KPIInstance'
const URL = '/v1/operational/kpi-instances'

export type KPIInstance = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']

export const useGetKPIInstances = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<KPIInstance[]>({
    axiosConfig,
    queryName: 'getKPIInstances',
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
