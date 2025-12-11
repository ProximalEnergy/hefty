import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'Company'
const URL = '/v1/admin/companies'

type Company = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']

export const useGetCompanies = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const axiosConfig = {
    url: URL,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  }

  return useCustomQuery<Company[]>({
    axiosConfig,
    queryName: 'getCompanies',
    pathParams: {},
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
