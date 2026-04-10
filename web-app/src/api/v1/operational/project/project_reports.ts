import type { components } from '@/api/schema'
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

export type SmartBidderMetricPayload =
  components['schemas']['BESSMonthlySmartBidderMetric']

export type GenerateBESSMonthlyReportPayload =
  components['schemas']['BESSMonthlyReportRequest']

interface PCSApparentVsVoltage {
  device_id: number
  x: number[]
  y: number[]
  device_name: string
}

export const useGetPCSApparentVsVoltage = ({
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
    url: `/v1/operational/projects/${pathParams.projectId}/reports/pcs-apparent-vs-voltage`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<PCSApparentVsVoltage[]>({
    axiosConfig,
    queryName: 'getPCSApparentVsVoltage',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGenerateEECBESSMonthlyReport = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      projectId,
      data,
    }: {
      projectId: string
      data: GenerateBESSMonthlyReportPayload
    }) => {
      const token = await getToken({ template: 'default' })
      await axios({
        method: 'post',
        url: `${baseURL}/v1/protected/web-application/projects/${projectId}/reports/eec-bess-monthly-report`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data,
      })
    },
    onSuccess: (_, variables) => {
      // Invalidate the reports list query to refetch after generation
      queryClient.invalidateQueries({
        queryKey: ['getBESSMonthlyReports', { projectId: variables.projectId }],
      })
    },
  })
}
