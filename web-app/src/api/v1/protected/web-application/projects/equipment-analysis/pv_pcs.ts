import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface EquipmentAnalysisPCSv2 {
  generating_power_block: {
    value: number[]
    total: number
  }
  generating_power_pcs: {
    value: number[]
    total: number
  }
  generating_power_pcs_module?: {
    value: number[]
    total: number
  }
  total_power_output: {
    value: number[]
    total_nameplate: number
  }
  block_power_distribution: {
    x: string[]
    y: number[][]
    customdata: number[]
    yaxis_range_max: number
  }
  block_power_distribution_norm: {
    x: string[]
    y: number[][]
    customdata: number[]
    yaxis_range_max: number
  }
  pcs_power_distribution: {
    x: string[]
    y: number[][]
    customdata: number[]
    yaxis_range_max: number
  }
  pcs_power_distribution_norm: {
    x: string[]
    y: number[][]
    customdata: number[]
    yaxis_range_max: number
  }
  pcs_module_power_distribution?: {
    x: string[]
    y: number[][]
    customdata: number[]
    yaxis_range_max: number
  }
}

export const useGetEquipmentAnalysisPCSv2 = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/equipment-analysis/pcs`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<EquipmentAnalysisPCSv2>({
    axiosConfig,
    queryName: 'getEquipmentAnalysisPCS',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
