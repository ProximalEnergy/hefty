import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const URL = '/v1/operational/projects/{project_id}/solar/position'

type SolarPositionResponse = {
  elevation_angle: number
  azimuth: number
  is_daytime: boolean
  next_sunrise: string | null
}

type getPathParams = {
  project_id: string
}

type getQueryParams = {
  timestamp?: string
}

export const useGetSolarPosition = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: getPathParams
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 30000, // 30 seconds
  }

  return useCustomQuery<SolarPositionResponse>({
    axiosConfig,
    queryName: 'getSolarPosition',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
