import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export interface CMMSTicket {
  cmms_provider: string
  id: number
  key: string
  created_at?: string
  due_date?: string
  summary?: string
  summary_long?: string
  status?: string
  status_change_at?: string
  priority?: string
  reporter?: string
  assigned_to?: string
  location?: string
  cmms_device_id?: string
  cmms_device_name?: string
  link?: string
}

interface CMMSMetadata {
  integration_configured: boolean
}

interface CMMSResponse {
  metadata: CMMSMetadata
  data: CMMSTicket[]
}

export const useGetCMMSTickets = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: { start?: string; end?: string; device_ids?: number[] }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/cmms-tickets/`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 5,
  }

  return useCustomQuery<CMMSResponse>({
    axiosConfig,
    queryName: 'getCMMSTickets',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
