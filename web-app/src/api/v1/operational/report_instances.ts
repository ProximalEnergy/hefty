import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

interface ReportType {
  report_type_id: number
  name_short: string
  name_long: string
  doc_url: string
}

interface ReportInstance {
  project_id: string
  report_type_id: number
  is_visible: boolean
  report_type?: ReportType
}

interface ReportInstanceUpdate {
  report_type_id: number
  is_visible: boolean
}

interface ReportInstancesBulkUpdate {
  report_instances: ReportInstanceUpdate[]
}

export const useGetReportTypes = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: '/v1/operational/report-types/',
  }

  return useCustomQuery<ReportType[]>({
    axiosConfig,
    queryName: 'getReportTypes',
    pathParams: {},
    queryParams: {},
    queryOptions,
  })
}

export const useBulkUpdateReportInstances = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation<
    ReportInstance[],
    Error,
    { projectId: string; data: ReportInstancesBulkUpdate }
  >({
    mutationFn: async ({ projectId, data }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'put',
        url: `${baseURL}/v1/operational/projects/${projectId}/report-instances/`,
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
        queryKey: ['getReportInstances', { projectId: variables.projectId }],
      })
    },
  })
}
