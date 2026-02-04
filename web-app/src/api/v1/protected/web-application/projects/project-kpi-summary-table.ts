import { components } from '@/api/schema'
import { Endpoint } from '@/api/utils'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export type KPISummaryTableRow = components['schemas']['KPISummaryTableRow']
// type KPISummaryTable = components['schemas']['KPISummaryTable']

const URL =
  '/v1/protected/web-application/projects/{project_id}/kpi-summary-table'

type GetProjectKPISummaryTable = Endpoint<typeof URL, 'get'>

export const useGetProjectKPISummaryTable = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: GetProjectKPISummaryTable['PathParams']
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 60 * 6, // 6 hours
  }
  return useCustomQuery<GetProjectKPISummaryTable['Response']>({
    axiosConfig,
    queryName: 'getProjectKPISummaryTable',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
