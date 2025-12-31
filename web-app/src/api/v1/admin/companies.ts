import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

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
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  }

  return useCustomQuery<Company[]>({
    axiosConfig,
    queryName: 'getCompanies',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useCreateCompany = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      name_short,
      name_long,
    }: {
      name_short: string
      name_long: string
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/admin/companies`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          name_short,
          name_long,
        },
      })
    },
    onSuccess: () => {
      // Invalidate any queries that fetch companies
      queryClient.invalidateQueries({ queryKey: ['getCompanies'] })
    },
  })
}
