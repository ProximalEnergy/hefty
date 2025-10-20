import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface ReportType {
  report_type_id: number
  name_short: string
  name_long: string
  doc_url: string
}

export const useGetReportType = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string; reportTypeId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/report-types/${pathParams.reportTypeId}`,
  }

  return useCustomQuery<ReportType>({
    axiosConfig,
    queryName: 'getReportType',
    pathParams,
    queryParams: {},
    queryOptions,
  })
}
