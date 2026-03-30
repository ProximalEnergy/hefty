import type * as types from '@/api/schema'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/react'
import { type UseQueryOptions, useQuery } from '@tanstack/react-query'
import axios from 'axios'

const URL =
  '/v1/protected/web-application/portfolio/market-performance/has-access'

type Row = types.components['schemas']['PortfolioMarketPerformanceHasAccessRow']
type Body =
  types.components['schemas']['PortfolioMarketPerformanceHasAccessRequest']

/**
 * Batch QSE market-performance access for many projects (one POST).
 *
 * Args:
 *   projectIds: Operational project UUID strings.
 */
export const usePortfolioMarketPerformanceHasAccess = ({
  projectIds,
  queryOptions = {},
}: {
  projectIds: string[]
  queryOptions?: Partial<UseQueryOptions<Row[]>>
}) => {
  const { getToken } = useAuth()
  const sortedKey = [...projectIds].sort().join(',')

  const defaultQueryOptions = {
    enabled: projectIds.length > 0,
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 60,
    retry: false,
  } satisfies Partial<UseQueryOptions<Row[]>>

  return useQuery({
    queryKey: ['postPortfolioMarketPerformanceHasAccess', sortedKey],
    queryFn: async (): Promise<Row[]> => {
      const token = await getToken({ template: 'default' })
      const body = { project_ids: projectIds } satisfies Body
      const { data } = await axios.post<Row[]>(`${baseURL}${URL}`, body, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      return data
    },
    ...defaultQueryOptions,
    ...queryOptions,
  })
}
