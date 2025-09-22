import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export interface TrackerEquipmentAnalysisData {
  position_from_setpoint: {
    by_block: { [key: string]: number }
    by_row: { [key: number]: { [rowKey: number]: number } }
  }
  setpoint_from_median: {
    by_block: { [key: string]: number }
    by_row: { [key: number]: { [rowKey: number]: number } }
  }
}

export const useGetTrackerEquipmentAnalysis = ({
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
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/equipment-analysis/tracker`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<TrackerEquipmentAnalysisData>({
    axiosConfig,
    queryName: 'getTrackerEquipmentAnalysis',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}
