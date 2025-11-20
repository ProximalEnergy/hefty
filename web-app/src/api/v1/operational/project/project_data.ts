import { useCustomQuery } from '@/hooks/api'
import * as types from '@/hooks/types'
import { UseQueryOptions } from '@tanstack/react-query'

export const useGetTimeSeries = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    tag_ids?: number[]
    device_ids?: number[]
    parent_device_id?: string
    sensor_type_name_shorts?: string[]
    sensor_type_ids?: number[]
    start?: string
    end?: string
    include_ghost_tags?: boolean
    interval?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const hasExcessTags = queryParams?.tag_ids && queryParams.tag_ids.length > 500

  const limitedQueryParams = hasExcessTags
    ? { ...queryParams, tag_ids: queryParams?.tag_ids?.slice(0, 500) }
    : queryParams

  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/time-series`,
    params: limitedQueryParams,
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
    params: queryParams,
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
    queryParams: queryParams,
    queryOptions: mergedQueryOptions,
  })
}
