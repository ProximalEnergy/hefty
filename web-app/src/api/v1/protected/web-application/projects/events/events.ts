import { useCustomQuery } from '@/hooks/api'
import * as types from '@/hooks/types'
import { UseQueryOptions } from '@tanstack/react-query'

interface EnrichedEvent extends types.Event {
  loss_daily_financial: number | null
}

interface HomepageSummary {
  top_events: EnrichedEvent[]
  total_daily_loss: number
  total_number_of_open_events: number
}

export interface EventMetrics {
  device_type_id: number
  device_type_name: string
  MTBF_hours: number
  MTTR_hours: number
  unavailability_contribution: number
  failure_count: number
}

interface EventsMetaAnalysis {
  metrics: EventMetrics[]
  daily_totals: {
    dates: string[]
    counts: number[]
  }
  device_totals: {
    device_type_id: number
    device_ids: number[]
    device_names: string[]
    total_failures: number[]
    total_hours: number[]
  }[]
}

export const useGetEventsMetaAnalysis = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: {
    projectId: string
  }
  queryParams: {
    start: string
    end: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/events/meta`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60,
  }

  return useCustomQuery<EventsMetaAnalysis>({
    axiosConfig,
    queryName: 'getEventsMetaAnalysis',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetHomepageSummary = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    sort_by?: 'daily' | 'total'
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/events/home-page-summary`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<HomepageSummary>({
    axiosConfig,
    queryName: 'getHomepageSummary',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
