import type * as types from '@/api/schema'
import type { Endpoint } from '@/api/utils'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useAuth } from '@clerk/react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

const URL_GET_USER_PROJECT_LABELS = '/v1/operational/user-project-labels'
type GetUserProjectLabels = Endpoint<typeof URL_GET_USER_PROJECT_LABELS, 'get'>

export type UserProjectLabel = types.components['schemas']['UserProjectLabel']
export type UserProjectLabelCreate =
  types.components['schemas']['UserProjectLabelCreate']
type UserProjectLabelUpdate = UserProjectLabel

export const useGetUserProjectLabels = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams?: GetUserProjectLabels['QueryParams']
  queryOptions?: Partial<UseQueryOptions<UserProjectLabel[]>>
} = {}) => {
  const axiosConfig = {
    url: URL_GET_USER_PROJECT_LABELS,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<UserProjectLabel[]>({
    axiosConfig,
    queryName: 'getUserProjectLabels',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useCreateUserProjectLabel = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<UserProjectLabel, Error, UserProjectLabelCreate>({
    mutationFn: async (labelData: UserProjectLabelCreate) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        url: `${baseURL}${URL_GET_USER_PROJECT_LABELS}`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: labelData,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['getUserProjectLabels'],
      })
    },
  })
}

export const useUpdateUserProjectLabel = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<
    UserProjectLabel,
    Error,
    { userProjectLabelId: number; labelData: UserProjectLabelUpdate }
  >({
    mutationFn: async ({ userProjectLabelId, labelData }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'put',
        url: `${baseURL}${URL_GET_USER_PROJECT_LABELS}/${userProjectLabelId}`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: labelData,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['getUserProjectLabels'],
      })
    },
  })
}

export const useDeleteUserProjectLabel = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<void, Error, { userProjectLabelId: number }>({
    mutationFn: async ({ userProjectLabelId }) => {
      const token = await getToken({ template: 'default' })
      await axios({
        method: 'delete',
        url: `${baseURL}${URL_GET_USER_PROJECT_LABELS}/${userProjectLabelId}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['getUserProjectLabels'],
      })
    },
  })
}
