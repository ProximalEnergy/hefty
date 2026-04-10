import type { Endpoint } from '@/api/utils'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

const URL_CMMS_PERMISSIONS =
  '/v1/operational/projects/{project_id}/cmms-permissions'
type GetCMMsPermissions = Endpoint<typeof URL_CMMS_PERMISSIONS, 'get'>

export const useGetCMMSPermissions = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: GetCMMsPermissions['PathParams']
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL_CMMS_PERMISSIONS,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<GetCMMsPermissions['Response']>({
    axiosConfig,
    queryName: 'getCMMSPermissions',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
