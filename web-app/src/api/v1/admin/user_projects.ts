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

interface UserProjectFavoriteUpdate {
  is_favorited: boolean
}

interface UserProject {
  user_id: string
  operational_project_id: string
  is_favorited: boolean
}

export const useUpdateProjectFavorite = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      userId,
      projectId,
      isFavorited,
    }: {
      userId: string
      projectId: string
      isFavorited: boolean
    }) => {
      const token = await getToken({ template: 'default' })

      const response = await axios({
        method: 'patch',
        url: `${baseURL}/v1/admin/user-projects/${userId}/projects/${projectId}/favorite`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: {
          is_favorited: isFavorited,
        } as UserProjectFavoriteUpdate,
      })
      return response.data
    },
    onMutate: async (newData) => {
      // Cancel any outgoing refetches (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: ['getUserProjects'] })

      // Snapshot the previous value
      const previousUserProjects = queryClient.getQueryData<UserProject[]>([
        'getUserProjects',
        { userId: newData.userId },
      ])

      // Optimistically update to the new value
      if (previousUserProjects) {
        const newUserProjects = previousUserProjects.map((project) =>
          project.operational_project_id === newData.projectId
            ? { ...project, is_favorited: newData.isFavorited }
            : project,
        )
        queryClient.setQueryData(
          ['getUserProjects', { userId: newData.userId }],
          newUserProjects,
        )
      }

      // Return a context object with the snapshotted value
      return { previousUserProjects }
    },
    onError: (_err, newData, context) => {
      // Rollback to the previous value if mutation fails
      if (context?.previousUserProjects) {
        queryClient.setQueryData(
          ['getUserProjects', { userId: newData.userId }],
          context.previousUserProjects,
        )
      }
    },
    onSettled: (_data, _error, variables) => {
      // Invalidate user projects queries to refresh favorited status
      queryClient.invalidateQueries({
        queryKey: ['getUserProjects', { userId: variables.userId }],
      })
      queryClient.invalidateQueries({ queryKey: ['getProjects'] })
      queryClient.invalidateQueries({ queryKey: ['getProjectsPersonal'] })
    },
  })
}

export const useGetUserProjects = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { userId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/user-projects/${pathParams.userId}`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.FIVE_MINUTES, // 5 minutes
  }

  return useCustomQuery<UserProject[]>({
    axiosConfig,
    queryName: 'getUserProjects',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
