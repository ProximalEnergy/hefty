import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { UseQueryOptions, useMutation } from '@tanstack/react-query'

export type PVBudgetedSeries = types.components['schemas']['PVBudgetedSeries']

export const useGetPVBudgetedSeries = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/pv-budgeted/series`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 0, // always consider stale so invalidation refetches immediately
    refetchOnMount: 'always',
  }

  return useCustomQuery<PVBudgetedSeries[]>({
    axiosConfig,
    queryName: 'pvBudgetedSeries',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useDeletePVBudgetedSeries = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async ({
      projectId,
      seriesId,
    }: {
      projectId: string
      seriesId: number
    }) => {
      const token = await getToken()
      const response = await fetch(
        `${baseURL}/v1/operational/projects/${projectId}/pv-budgeted/series/${seriesId}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        },
      )

      if (!response.ok) {
        throw new Error('Failed to delete series')
      }

      return response.json()
    },
    mutationKey: ['deletePVBudgetedSeries'],
  })
}
