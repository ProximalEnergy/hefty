import type { components } from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

export const useGetProjectBessWaterfall = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    start: string
    end: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/bess-waterfall`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.SIX_HOURS, // 6 hours
  }

  return useCustomQuery<components['schemas']['ProjectBessWaterfallResponse']>({
    axiosConfig,
    queryName: 'getProjectBessWaterfall',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetBessAuxEnergyDailyAvg = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    start: string
    end: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/bess-waterfall/aux-energy-daily-avg`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.SIX_HOURS, // 6 hours
  }

  return useCustomQuery<components['schemas']['AuxEnergyDailyAvgResponse']>({
    axiosConfig,
    queryName: 'getProjectBessAuxEnergyDailyAvg',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
