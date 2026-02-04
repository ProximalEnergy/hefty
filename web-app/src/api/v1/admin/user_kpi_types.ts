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

const URL = '/v1/admin/user-kpi-types/favorite'
const _COMPONENT_NAME = 'UserKPITypes'

type UserKPIType = types.components['schemas'][typeof _COMPONENT_NAME]

export const useGetUserFavoriteKPITypes = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  return useCustomQuery<UserKPIType[]>({
    axiosConfig,
    queryName: 'getUserFavoriteKPITypes',
    queryParams: {},
    queryOptions,
  })
}

export const useUpdateUserKPITypeFavoriteMutation = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      kpiTypeId,
      isFavorited,
    }: {
      kpiTypeId: number
      isFavorited: boolean
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'patch',
        url: `${baseURL}/v1/admin/user-kpi-types/favorite`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          kpi_type_id: kpiTypeId,
          is_favorited: isFavorited,
        },
      })
    },
    onMutate: async ({ kpiTypeId, isFavorited }) => {
      const queryKey = ['getUserFavoriteKPITypes']
      await queryClient.cancelQueries({ queryKey })

      const previousFavorites =
        queryClient.getQueryData<UserKPIType[]>(queryKey)

      queryClient.setQueryData(queryKey, (old?: UserKPIType[]) => {
        if (!old) {
          return isFavorited
            ? [{ user_id: '', kpi_type_id: kpiTypeId, is_favorited: true }]
            : []
        }

        const existing = old.find((f) => f.kpi_type_id === kpiTypeId)
        const userId = old[0]?.user_id || ''

        if (isFavorited) {
          if (existing) {
            return old.map((f) =>
              f.kpi_type_id === kpiTypeId ? { ...f, is_favorited: true } : f,
            )
          }
          return [
            ...old,
            { user_id: userId, kpi_type_id: kpiTypeId, is_favorited: true },
          ]
        } else {
          return old.filter((f) => f.kpi_type_id !== kpiTypeId)
        }
      })

      return { previousFavorites, queryKey }
    },
    onError: (_err, _variables, context) => {
      if (context?.previousFavorites) {
        queryClient.setQueryData(context.queryKey, context.previousFavorites)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ['getUserFavoriteKPITypes'],
      })
    },
  })
}
