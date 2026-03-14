import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

const _COMPONENT_NAME = 'APIKey'
const URL = '/v1/admin/api-key'

type APIKey = types.components['schemas'][typeof _COMPONENT_NAME]

export const useGetApiKey = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<APIKey>({
    axiosConfig,
    queryName: 'getApiKey',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useCreateApiKeyMutation = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/admin/api-key`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getApiKey'] })
    },
  })
}

export const useDeleteApiKeyMutation = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'delete',
        url: `${baseURL}/v1/admin/api-key`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getApiKey'] })
    },
  })
}
