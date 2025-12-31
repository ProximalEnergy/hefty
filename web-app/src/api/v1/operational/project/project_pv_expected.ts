import { useCustomQuery } from '@/hooks/api'
import * as types from '@/hooks/types'
import { UseQueryOptions } from '@tanstack/react-query'

export const useGetPvExpected = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    start: string
    end: string
    device_ids?: number[]
    expected_metric_ids?: number[]
    highest_priority_only?: boolean
    cutoff_now?: boolean
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/pv-expected`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  const mergedQueryOptions = {
    ...defaultQueryOptions,
    ...queryOptions,
  }

  return useCustomQuery<types.DataTimeSeries[]>({
    axiosConfig,
    queryName: 'getTimeSeries',
    pathParams,
    queryParams,
    queryOptions: mergedQueryOptions,
  })
}
