import type * as types from '@/api/schema'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'

const _COMPONENT_NAME_REPORT_INSTANCE = 'ReportInstance'
const _COMPONENT_NAME_REPORT_INSTANCES_BULK_UPDATE = 'ReportInstancesBulkUpdate'

type ReportInstance =
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
