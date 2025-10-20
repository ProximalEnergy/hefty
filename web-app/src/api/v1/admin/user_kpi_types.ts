import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

interface UserKPIType {
  user_id: string
  kpi_type_id: number
  is_favorited: boolean
}

export const useGetUserFavoriteKPITypes = ({
  userId,
  queryOptions = {},
}: {
  userId: string | undefined
  queryOptions?: Partial<UseQueryOptions<UserKPIType[]>>
}) => {
  return useCustomQuery<UserKPIType[]>({
    axiosConfig: { url: `/v1/admin/user-kpi-types/favorite` },
    queryName: 'getUserFavoriteKPITypes',
    queryParams: { user_id: userId },
    queryOptions: {
      enabled: !!userId,
      ...queryOptions,
    },
  })
}

export const useUpdateUserKPITypeFavoriteMutation = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      userId,
      kpiTypeId,
      isFavorited,
    }: {
      userId: string
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
          user_id: userId,
          kpi_type_id: kpiTypeId,
          is_favorited: isFavorited,
        },
      })
    },
    onMutate: async ({ userId, kpiTypeId, isFavorited }) => {
      const queryKey = ['getUserFavoriteKPITypes', { user_id: userId }]
      await queryClient.cancelQueries({ queryKey })

      const previousFavorites =
        queryClient.getQueryData<UserKPIType[]>(queryKey)

      queryClient.setQueryData(queryKey, (old?: UserKPIType[]) => {
        if (!old) {
          return isFavorited
            ? [{ user_id: userId, kpi_type_id: kpiTypeId, is_favorited: true }]
            : []
        }

        const existing = old.find((f) => f.kpi_type_id === kpiTypeId)

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
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['getUserFavoriteKPITypes', { user_id: variables.userId }],
      })
    },
  })
}
