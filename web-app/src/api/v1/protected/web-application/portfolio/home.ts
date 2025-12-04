import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

type PortfolioHomeProject = {
  project_id: string
  // Short-term fields (24h)
  power?: number | null
  poa?: number | null
  soc?: number | null
  times?: string[] | null
  meter_active_power?: number[] | null
  meter_soc_percent?: number[] | null
  max_charge_power?: number[] | null
  max_discharge_power?: number[] | null
  // Long-term fields (30d)
  cycle_count_string?: number[] | null
  state_of_health?: number[] | null
  pcs_mechanical_availability?: number[] | null
  energy_production?: number[] | null
  expected_power?: number[] | null
  performance_index?: number | null
}

export const useGetPortfolioHome = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    project_ids?: string[]
    time?: '24h' | '30d'
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/portfolio/home`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    staleTime: 1000 * 60 * 5,
  }

  return useCustomQuery<PortfolioHomeProject[]>({
    axiosConfig,
    queryName: 'getPortfolioHome',
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
