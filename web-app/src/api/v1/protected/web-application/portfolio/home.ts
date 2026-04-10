import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'PortfolioHome'
const URL = '/v1/protected/web-application/portfolio/home'

type PortfolioHome = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']

export const useGetPortfolioHome = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {
    staleTime: QUERY_TIME.FIVE_MINUTES,
    refetchInterval: QUERY_TIME.FIVE_MINUTES,
  }

  return useCustomQuery<PortfolioHome[]>({
    axiosConfig,
    queryName: 'getPortfolioHome',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
