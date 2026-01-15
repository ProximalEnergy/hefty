import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface Data {
  times: string[]
  positions: { [key: string]: number[] }
  setpoints: { [key: string]: number[] }
}

export const useGetEquipmentAnalysisTrackerBlock = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string; deviceId: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/equipment-analysis/tracker/${pathParams.deviceId}`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<Data>({
    axiosConfig,
    queryName: 'getEquipmentAnalysisTrackerBlock',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
