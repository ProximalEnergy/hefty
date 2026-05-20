import { paths } from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import type { DataTimeSeries } from '@/hooks/types'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const URL = '/v1/operational/projects/{project_id}/time-series'

type get = paths[typeof URL]['get']
type getPathParams = get['parameters']['path']
type getQueryParams = get['parameters']['query']

export const useGetTimeSeries = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: getPathParams
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const hasExcessTags = queryParams?.tag_ids && queryParams.tag_ids.length > 500

  const limitedQueryParams = hasExcessTags
    ? { ...queryParams, tag_ids: queryParams?.tag_ids?.slice(0, 500) }
    : queryParams

  const axiosConfig = { url: URL }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  const mergedQueryOptions = {
    ...defaultQueryOptions,
    ...queryOptions,
  }

  return useCustomQuery<DataTimeSeries[]>({
    axiosConfig,
    queryName: 'getTimeSeries',
    pathParams,
    queryParams: limitedQueryParams,
    queryOptions: mergedQueryOptions,
  })
}

export const useGetDataTimeSeriesV3 = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    tag_ids?: number[]
    sensor_type_ids?: number[]
    start?: string
    end?: string
    ensure_full_range?: boolean
    interval?: string
    cutoff_now?: boolean
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/data-timeseries-v3`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  const mergedQueryOptions = {
    ...defaultQueryOptions,
    ...queryOptions,
  }

  return useCustomQuery<DataTimeSeries[]>({
    axiosConfig,
    queryName: 'getTimeSeries',
    pathParams,
    queryParams,
    queryOptions: mergedQueryOptions,
  })
}
