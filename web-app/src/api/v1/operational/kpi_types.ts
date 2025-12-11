import { DeviceType } from '@/api/v1/operational/device_types'
import { useCustomQuery } from '@/hooks/api'
import { KPITypeWithContracts } from '@/hooks/types'
import { UseQueryOptions } from '@tanstack/react-query'

export interface KPIType {
  kpi_type_id: number
  device_type_id: number
  name_short: string
  name_long: string
  name_metric: string
  description: string
  unit: string
  aggregation_method: string
  device_type?: DeviceType
  doc_url?: string
}

interface ContractInfo {
  contract_id: number
  project_id: string
  execution_date: string
  provider_company: string
  counter_company: string
}

interface ContractKPIInfo {
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

export interface KPITypeWithContractInfo extends KPIType {
  contract_kpis: ContractKPIInfo[]
  contracts: ContractInfo[]
  is_visible: boolean
}

export const useGetKPITypes = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
  queryParams?: {
    kpi_type_ids?: number[]
  }
}) => {
  const axiosConfig = {
    url: '/v1/operational/kpi-types',
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<KPIType[]>({
    axiosConfig,
    queryName: 'getKPITypes',
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetProjectKPITypes = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/kpi-types/by-project/${pathParams.projectId}`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  }

  return useCustomQuery<KPITypeWithContractInfo[]>({
    axiosConfig,
    queryName: `getProjectKPITypes-${pathParams.projectId}`,
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetKPITypeByName = ({
  pathParams,
}: {
  pathParams: { nameShort: string }
}) => {
  const axiosConfig = {
    method: 'GET',
    url: `/v1/operational/kpi-types/by-name/${pathParams.nameShort}`,
  }

  return useCustomQuery<KPITypeWithContracts>({
    axiosConfig,
    queryName: 'getKPITypeByName',
  })
}
