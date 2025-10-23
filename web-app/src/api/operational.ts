import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

import { User } from './admin'

export const useGetCompanyUsers = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/users/`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<User[]>({
    axiosConfig,
    queryName: 'getCompanyUsers',
    pathParams: {},
    queryParams: {},
    queryOptions: queryOptions,
  })
}
