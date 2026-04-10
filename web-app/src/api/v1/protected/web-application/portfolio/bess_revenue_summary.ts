import type * as types from '@/api/schema'
import { baseURL } from '@/urlConfig'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useAuth } from '@clerk/react'
import { type UseQueryOptions, useQuery } from '@tanstack/react-query'
import axios from 'axios'

const URL = '/v1/protected/web-application/portfolio/bess-revenue-summary'

type Row = types.components['schemas']['PortfolioBessRevenueSummaryRow']
type Body = types.components['schemas']['PortfolioBessRevenueSummaryRequest']

/**
 * Batch fetch QSE settlement revenue (today/MTD/YTD) for many BESS projects
 * in a single POST, avoiding the N+1 per-project request pattern.
 *
 * Args:
 *   projectIds: Operational project UUID strings (BESS / PVS projects).
 */
export const usePortfolioBessRevenueSummary = ({
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
    staleTime: QUERY_TIME.THIRTY_MINUTES,
    retry: false,
  } satisfies Partial<UseQueryOptions<Row[]>>

  return useQuery({
    queryKey: ['postPortfolioBessRevenueSummary', sortedKey],
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

export type { Row as PortfolioBessRevenueSummaryRow }
