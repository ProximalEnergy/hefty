import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

import { KPIType } from './kpi_types'

export interface KPIInstance {
  project_id: string
  kpi_type_id: number
  is_visible: boolean

  // Relationships
  kpi_type?: KPIType
}

export const useGetKPIInstances = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    kpi_type_ids?: number[]
    project_ids?: string[]
    deep?: boolean
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/kpi-instances/`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<KPIInstance[]>({
    axiosConfig,
    queryName: 'getKPIInstances',
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
