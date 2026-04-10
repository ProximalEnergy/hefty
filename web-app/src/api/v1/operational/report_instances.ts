import type * as types from '@/api/schema'
import type { Endpoint } from '@/api/utils'
import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useAuth } from '@clerk/react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

const URL_GET_REPORT_INSTANCES = '/v1/operational/report-instances'
type GetReportInstances = Endpoint<typeof URL_GET_REPORT_INSTANCES, 'get'>

export const useGetReportInstances = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: GetReportInstances['QueryParams']
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL_GET_REPORT_INSTANCES,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<GetReportInstances['Response']>({
    axiosConfig,
    queryName: 'getReportInstances',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

const _COMPONENT_NAME_REPORT_INSTANCE = 'ReportInstance'
const _COMPONENT_NAME_REPORT_INSTANCES_BULK_UPDATE = 'ReportInstancesBulkUpdate'

export type ReportInstance =
  types.components['schemas'][typeof _COMPONENT_NAME_REPORT_INSTANCE]
type ReportInstancesBulkUpdate =
  types.components['schemas'][typeof _COMPONENT_NAME_REPORT_INSTANCES_BULK_UPDATE]

export const useBulkUpdateReportInstances = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<
    ReportInstance[],
    Error,
    { project_id: string; data: ReportInstancesBulkUpdate }
  >({
    mutationFn: async ({ project_id, data }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'put',
        url: `${baseURL}/v1/operational/projects/${project_id}/report-instances`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data,
      })
      return response.data
    },
    onSuccess: (_, variables) => {
      // Invalidate report instances query for this project
      queryClient.invalidateQueries({
        queryKey: ['getReportInstances', { project_id: variables.project_id }],
      })
    },
  })
}
