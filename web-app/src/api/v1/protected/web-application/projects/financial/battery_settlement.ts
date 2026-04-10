import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

interface BatterySettlementDetails {
  qse_data: {
    index: string[]
    data: Record<string, (number | null)[]>
    unit: Record<string, string>
  }
  calculated_data: {
    index: string[]
    data: Record<string, (number | null)[]>
    unit: Record<string, string>
  }
  tsk_identifier: string
}

export const useGetBatterySettlementDetails = ({
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
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/battery-settlement`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.SIX_HOURS, // 6 hours
  }

  const mergedQueryOptions = { ...defaultQueryOptions, ...queryOptions }
  return useCustomQuery<BatterySettlementDetails>({
    axiosConfig,
    queryName: 'getBatterySettlementDetails',
    pathParams,
    queryParams,
    queryOptions: mergedQueryOptions,
  })
}
