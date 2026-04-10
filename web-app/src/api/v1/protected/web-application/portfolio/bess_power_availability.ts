import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const URL = '/v1/protected/web-application/portfolio/bess-power-availability'

interface PortfolioBessPowerAvailabilityRow {
  project_id: string
  available_power_mw: number | null
  poi_capacity_mw: number | null
  max_pcs_capacity_mw: number | null
  num_pcs_units: number | null
  power_availability_pct_poi: number | null
  power_availability_pct_pcs: number | null
}

/**
 * One request: latest PCS power availability (% of POI) for many projects
 * from operational.data_timeseries (DISTINCT ON per tag).
 *
 * Args:
 *   projectIds: BESS and PVS project IDs to include.
 */
export const usePortfolioBessPowerAvailability = ({
  projectIds,
  queryOptions = {},
}: {
  projectIds: string[]
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {
    enabled: projectIds.length > 0,
    refetchInterval: QUERY_TIME.ONE_MINUTE,
    staleTime: QUERY_TIME.THIRTY_SECONDS,
    refetchOnWindowFocus: false,
  }

  return useCustomQuery<PortfolioBessPowerAvailabilityRow[]>({
    axiosConfig,
    queryName: 'getPortfolioBessPowerAvailability',
    queryParams: { project_ids: projectIds },
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export type { PortfolioBessPowerAvailabilityRow }
