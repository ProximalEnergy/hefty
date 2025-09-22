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
  const axiosConfig = {
    url: `/v1/analytics/${pathParams.projectId}/tracking-angles`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<TrackingAngles>({
    axiosConfig,
    queryName: 'getTrackingAngles',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}
