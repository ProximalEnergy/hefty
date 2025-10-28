import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

type PortfolioHomeProject = {
  project_id: string
  power?: number
  poa?: number
  soc?: number
  times?: string[]
  meter_active_power?: number[]
  meter_soc_percent?: number[]
  max_charge_power?: number[]
  max_discharge_power?: number[]
}

export const useGetPortfolioHome = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    project_ids?: string[]
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

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<PortfolioHomeProject[]>({
    axiosConfig,
    queryName: 'getPortfolioHome',
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}
