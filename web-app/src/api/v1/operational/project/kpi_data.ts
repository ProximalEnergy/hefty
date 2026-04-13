import type { components } from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

export type KPISummaryCard = components['schemas']['KPISummary'] & {
  suffix?: string
  icon?: React.ReactNode
  onClick?: () => void
}

export const useGetKPISummaryCards = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    contract_id?: number
    kpi_type_ids?: number[]
    date?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/kpi-data/kpi-summary-cards`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.SIX_HOURS, // 6 hours
  }
  return useCustomQuery<KPISummaryCard[]>({
    axiosConfig,
    queryName: 'getKPISummaryCards',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetRoundTripEfficiency = ({
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
    url: `/v1/operational/projects/${pathParams.projectId}/kpi-data/rte`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.SIX_HOURS, // 6 hours
  }
  return useCustomQuery<components['schemas']['RTEResponse']>({
    axiosConfig,
    queryName: 'getRoundTripEfficiency',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

type RTEType = 'POI' | 'POI_NO_AUX' | 'FEEDER' | 'DC'

export const useGetRoundTripEfficiencyV2 = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    start: string
    end: string
    rte_type: RTEType
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/kpi-data/rte-v2`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.SIX_HOURS, // 6 hours
  }
  return useCustomQuery<components['schemas']['RTEResponse']>({
    axiosConfig,
    queryName: 'getRoundTripEfficiencyV2',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
