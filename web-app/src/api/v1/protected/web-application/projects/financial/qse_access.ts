import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

interface QSEAccessResponse {
  has_access: boolean
}

export const useGetQSEAccess = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/market-performance/has-access`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.ONE_HOUR, // 1 hour
    retry: false,
  } satisfies Partial<UseQueryOptions>

  return useCustomQuery<QSEAccessResponse>({
    axiosConfig,
    queryName: 'getQSEAccess',
    pathParams,
    queryParams: {},
    queryOptions: {
      ...defaultQueryOptions,
      ...queryOptions,
    },
  })
}
