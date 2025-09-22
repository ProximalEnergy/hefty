import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export interface Company {
  company_id: string
  name_short: string
  name_long: string
}

export const useGetCompanies = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    company_ids?: string[]
    name_shorts?: string[]
  }
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const axiosConfig = {
    url: '/v1/admin/companies',
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<Company[]>({
    axiosConfig,
    queryName: 'getCompanies',
    pathParams: {},
    queryParams,
    queryOptions: queryOptions,
  })
}
