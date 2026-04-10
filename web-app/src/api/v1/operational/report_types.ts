import type { Endpoint } from '@/api/utils'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const URL_REPORT_TYPE = '/v1/operational/report-types/{report_type_id}'
const URL_REPORT_TYPES = '/v1/operational/report-types'

type GetReportType = Endpoint<typeof URL_REPORT_TYPE, 'get'>
type GetReportTypes = Endpoint<typeof URL_REPORT_TYPES, 'get'>

export const useGetReportType = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: GetReportType['PathParams']
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL_REPORT_TYPE,
  }

  return useCustomQuery<GetReportType['Response']>({
    axiosConfig,
    queryName: 'getReportType',
    pathParams,
    queryOptions,
  })
}

export const useGetReportTypes = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL_REPORT_TYPES,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<GetReportTypes['Response']>({
    axiosConfig,
    queryName: 'getReportTypes',
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
