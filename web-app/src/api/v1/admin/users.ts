import type { Endpoint } from '@/api/utils'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const URL_GET_USERS = '/v1/admin/users'
type GetUsers = Endpoint<typeof URL_GET_USERS, 'get'>

export const useGetUsers = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: GetUsers['QueryParams']
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = { url: URL_GET_USERS }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<GetUsers['Response']>({
    axiosConfig,
    queryName: 'getUsers',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

const URL_GET_USER_SELF = '/v1/admin/users/self'
type GetUserSelf = Endpoint<typeof URL_GET_USER_SELF, 'get'>

export const useGetUserSelf = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = { url: URL_GET_USER_SELF }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<GetUserSelf['Response']>({
    axiosConfig,
    queryName: 'getUserSelf',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

const URL_USERS_SELF_COMPANY = '/v1/admin/users/self-company'
type GetSelfCompanyUsers = Endpoint<typeof URL_USERS_SELF_COMPANY, 'get'>

export const useGetSelfCompanyUsers = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = { url: URL_USERS_SELF_COMPANY }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<GetSelfCompanyUsers['Response']>({
    axiosConfig,
    queryName: 'getUserSelfCompany',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
