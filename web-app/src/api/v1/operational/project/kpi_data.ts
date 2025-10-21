import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export interface KPISummaryCard {
  kpi_type_id: number
  contract_id: number | null
  link: string
  is_visible: boolean
  ytd_value?: number | null
  title: string
  info?: string
  value?: number
  prefix?: string
  suffix?: string
  unit?: string
  change?: number
  icon?: React.ReactNode
  valColor?: string
  aggregation_method?: string
  onClick?: () => void
}

export const useGetKPISummaryCards = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    kpi_type_ids?: number[]
    date?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/kpi-data/kpi-summary-cards`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 60 * 6, // 6 hours
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }
  return useCustomQuery<KPISummaryCard[]>({
    axiosConfig,
    queryName: 'getKPISummaryCards',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}
