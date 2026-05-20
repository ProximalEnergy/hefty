import { useCustomQuery } from '@/hooks/api'
import type { Event } from '@/hooks/types'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

export interface EnrichedEvent extends Event {
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
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.ONE_MINUTE,
  }

  return useCustomQuery<EventsMetaAnalysis>({
    axiosConfig,
    queryName: 'getEventsMetaAnalysis',
    pathParams,
    queryParams,
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
    url:
      `/v1/protected/web-application/projects/${pathParams.projectId}` +
      '/events/home-page-summary',
  }

  const defaultQueryOptions = {}

  return useCustomQuery<HomepageSummary>({
    axiosConfig,
    queryName: 'getHomepageSummary',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
