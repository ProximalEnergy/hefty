import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface PTPEndpoint {
  keyName: string
  values: Array<{
    intervalStartUtc: string
    intervalEndUtc: string
    data: Array<{
      value: number | null
    }>
  }>
}

interface PTPElement {
  identifier: string
  element: string
  definition: string
  parent?: string
  parentIdentifier?: string
  parentDefinition?: string
  goLiveDate?: string
  expirationDate?: string
  dataPoints: PTPEndpoint[]
}

interface PTPDataResponse {
  data: PTPElement[]
}

interface PTPEndpointsResponse {
  categories: {
    performance: string[]
    settlement: string[]
    market: string[]
    analysis: string[]
    submissions: string[]
  }
  identifiers: {
    generator_id: string
    entity_id: string
    resource_id: string
    settlement_point_id: string
    cop_id: string
  }
  availability?: Record<string, boolean>
}

export const useGetPTPEndpoints = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/ptp-data/endpoints`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnMount: true,
    refetchOnReconnect: false,
  } satisfies Partial<UseQueryOptions>

  const mergedQueryOptions = { ...defaultQueryOptions, ...queryOptions }
  return useCustomQuery<PTPEndpointsResponse>({
    axiosConfig,
    queryName: 'getPTPEndpoints',
    pathParams,
    queryParams: {},
    queryOptions: mergedQueryOptions,
  })
}

export const useGetPTPData = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    endpoint: string
    category: string
    start?: string
    end?: string
    element_id?: string
    data_points?: string[]
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/ptp-data/data`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 60 * 1000, // 1 minute
    refetchOnMount: true,
    refetchOnReconnect: false,
  } satisfies Partial<UseQueryOptions>

  const mergedQueryOptions = { ...defaultQueryOptions, ...queryOptions }
  return useCustomQuery<PTPDataResponse>({
    axiosConfig,
    queryName: 'getPTPData',
    pathParams,
    queryParams: queryParams,
    queryOptions: mergedQueryOptions,
  })
}

export const useGetPTPEndpointsAvailability = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    category: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/ptp-data/endpoints/availability`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes - availability doesn't change often
    refetchOnMount: false,
    refetchOnReconnect: false,
  } satisfies Partial<UseQueryOptions>

  const mergedQueryOptions = { ...defaultQueryOptions, ...queryOptions }
  return useCustomQuery<Record<string, boolean>>({
    axiosConfig,
    queryName: 'getPTPEndpointsAvailability',
    pathParams,
    queryParams: queryParams,
    queryOptions: mergedQueryOptions,
  })
}

interface OutageTicket {
  identifier: string
  element: string
  outage_status?: string | null
  planned_start_time?: string | null
  planned_end_time?: string | null
  actual_end_time?: string | null
  station?: string | null
  resource_id?: string | null
  data_points?: Record<string, unknown> | null
  go_live_date?: string | null
  expiration_date?: string | null
  parent_identifier?: string | null
  is_active?: boolean
}

interface ActiveOutageTicketsResponse {
  active_tickets: number
  tickets: OutageTicket[]
}

export const useGetActiveOutageTickets = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    resource_name?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/ptp-data/active-outage-tickets`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 2 * 60 * 1000, // 2 minutes - outage tickets can change
    refetchOnMount: true,
    refetchOnReconnect: false,
  } satisfies Partial<UseQueryOptions>

  const mergedQueryOptions = { ...defaultQueryOptions, ...queryOptions }
  return useCustomQuery<ActiveOutageTicketsResponse>({
    axiosConfig,
    queryName: 'getActiveOutageTickets',
    pathParams,
    queryParams: queryParams || {},
    queryOptions: mergedQueryOptions,
  })
}
