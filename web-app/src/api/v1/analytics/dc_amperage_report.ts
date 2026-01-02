import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export interface CombinerHealth {
  columns: string[]
  index: string[]
  data: Array<Array<number | null>>
}

export interface DCAmperageDataV2 {
  inv: CombinerHealth
  proj: CombinerHealth
  reports: {
    excel: string
    poa: string
    cb: string
  }
}

export const useGetDCAmperageReportV2 = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    start: string
    min_poa: number
    max_poa_1d: number
    max_poa_std: number
    rolling_window: number
    use_poa_1d: boolean
    use_poa_std: boolean
    resample_rate: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url:
      `/v1/operational/projects/${pathParams.projectId}` +
      '/reports/dc-amperage-report-v2',
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<DCAmperageDataV2>({
    axiosConfig,
    queryName: 'getDCAmperageReportV2',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
