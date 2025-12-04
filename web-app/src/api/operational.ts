import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

import { User } from './admin'

export const useGetCompanyUsers = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    user_ids?: string[]
    include_image_urls?: boolean
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/users/`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<User[]>({
    axiosConfig,
    queryName: 'getCompanyUsers',
    pathParams: {},
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
