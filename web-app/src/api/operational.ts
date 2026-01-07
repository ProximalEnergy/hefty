import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

type OperationalUser = types.components['schemas']['UserWithProjects']

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
    url: `/v1/operational/users`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<OperationalUser[]>({
    axiosConfig,
    queryName: 'getCompanyUsers',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
