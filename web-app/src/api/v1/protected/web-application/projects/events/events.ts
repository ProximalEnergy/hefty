import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

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
