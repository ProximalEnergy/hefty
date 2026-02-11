import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface RealtimePriceResponse {
  price: number | null
  timestamp: string | null
  unit: string
  settlement_point: string
  qse_provider_name: string | null
  node_name: string
}

export const useGetRealtimePrice = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/market-performance/realtime/price`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 60 * 1000, // 1 minute - prices update every 15 minutes
    refetchInterval: 60 * 1000, // Refetch every minute to get latest price
    refetchOnMount: true,
    refetchOnReconnect: false,
  } satisfies Partial<UseQueryOptions>

  const mergedQueryOptions = { ...defaultQueryOptions, ...queryOptions }
  return useCustomQuery<RealtimePriceResponse>({
    axiosConfig,
    queryName: 'getRealtimePrice',
    pathParams,
    queryParams: {},
    queryOptions: mergedQueryOptions,
  })
}

interface ProjectIdentifier {
  identifier: string
  element: string
  definition: string
  resource_id: string | null
  parent_identifier: string | null
  is_parent: boolean
}

interface ProjectIdentifiersResponse {
  identifiers: ProjectIdentifier[]
  parent_identifier: string
  market_participant_identifier: string | null
}

export const useGetProjectIdentifiers = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/market-performance/identifiers`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 30 * 60 * 1000, // 30 minutes - identifiers don't change often
    refetchOnMount: true,
    refetchOnReconnect: false,
  } satisfies Partial<UseQueryOptions>

  const mergedQueryOptions = { ...defaultQueryOptions, ...queryOptions }
  return useCustomQuery<ProjectIdentifiersResponse>({
    axiosConfig,
    queryName: 'getProjectIdentifiers',
    pathParams,
    queryParams: {},
    queryOptions: mergedQueryOptions,
  })
}
