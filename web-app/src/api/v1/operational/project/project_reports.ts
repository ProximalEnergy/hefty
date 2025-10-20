import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface PCSApparentVsVoltage {
  device_id: number
  x: number[]
  y: number[]
  device_name: string
}

export const useGetPCSApparentVsVoltage = ({
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
    url: `/v1/operational/projects/${pathParams.projectId}/reports/pcs-apparent-vs-voltage`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<PCSApparentVsVoltage[]>({
    axiosConfig,
    queryName: 'getPCSApparentVsVoltage',
    pathParams,
    queryParams,
    queryOptions: queryOptions,
  })
}
