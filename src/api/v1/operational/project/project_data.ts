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
    start?: string
    end?: string
    include_ghost_tags?: boolean
    interval?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  if (queryParams?.tag_ids && queryParams.tag_ids.length > 500) {
    queryParams.tag_ids = queryParams.tag_ids.slice(0, 500)
  }

  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/time-series`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<types.DataTimeSeries[]>({
    axiosConfig,
    queryName: 'getTimeSeries',
    pathParams,
    queryParams,
    queryOptions: queryOptions,
  })
}
