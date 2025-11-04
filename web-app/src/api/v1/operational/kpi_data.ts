import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export interface OperationalKPIData {
  project_id: string
  kpi_type_id: number
  data: DataBlock
}

interface DataBlock {
  dates: string[]
  project_data: (number | null)[]
  weight?: (number | null)[]
  device_data_obj?: DeviceDataObj
  device_aggregation_obj?: DeviceAggregationObj
}

interface DeviceDataObj {
  device_values: { [deviceId: string]: (number | null)[] }
}

interface DeviceAggregationObj {
  sum?: (number | null)[]
  mean?: (number | null)[]
  std?: (number | null)[]
  min?: (number | null)[]
  max?: (number | null)[]
  median?: (number | null)[]
  count?: (number | null)[]
  range?: (number | null)[]
  available_data?: (number | null)[]
}

export const useGetOperationalKPIData = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    start?: string
    end?: string
    include_device_data?: boolean
    project_ids?: string[]
    kpi_type_ids?: number[]
    include_all_dates?: boolean
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/kpi-data/`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 60 * 6, // 6 hours
  }
  return useCustomQuery<OperationalKPIData[]>({
    axiosConfig,
    queryName: 'getOperationalKPIData',
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// Add this interface near your other interfaces
interface ContractKPI {
  contract_id: number
  kpi_type_id: number
  threshold?: {
    values: {
      [key: string]: number
    }
  }
  liquidated_damages?: object
  claim_howto?: object
  provider_responsible?: boolean
}

export const useGetContractKPIs = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    method: 'get',
    url: `/v1/operational/projects/${pathParams.projectId}/kpi-data/contract-kpis`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  }

  return useCustomQuery<ContractKPI[]>({
    axiosConfig,
    queryName: 'getContractKPIs',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetKPIExcel = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    kpi_type_id: number
    start: string
    end: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    method: 'get',
    url: `/v1/operational/kpi-data/${pathParams.projectId}/excel`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  }

  return useCustomQuery<string>({
    axiosConfig,
    queryName: 'getKPIExcel',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
