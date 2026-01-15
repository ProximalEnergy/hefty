import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface WaterfallData {
  value: number[]
  measure: string[]
  name: string[]
}

export const useGetWaterfall = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    level?: string
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/waterfall`,
  }

  const defaultQueryOptions = {
    staleTime: 5 * 60 * 1000,
  }

  return useCustomQuery<WaterfallData>({
    axiosConfig,
    queryName: 'getWaterfall',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
