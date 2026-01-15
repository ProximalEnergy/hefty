import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

type TrackingAngles = {
  times: string[]
  tracker_theta: number[]
}

export const useGetTrackingAngles = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const resolvedQueryParams = {
    ...queryParams,
    project_id: pathParams.projectId,
  }

  const axiosConfig = {
    url: '/v1/trackers/tracking-angles',
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<TrackingAngles>({
    axiosConfig,
    queryName: 'getTrackingAngles',
    pathParams,
    queryParams: resolvedQueryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
