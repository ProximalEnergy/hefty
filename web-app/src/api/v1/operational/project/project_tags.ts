import { useCustomQuery } from '@/hooks/api'
import * as types from '@/hooks/types'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

export const useGetTagsByRegex = ({
  pathParams,
  queryParams = {
    regex: '',
    limit: 200,
    deep: false,
  },
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    regex: string
    limit: number
    deep?: boolean
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/tags/regex`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<types.Tag[]>({
    axiosConfig,
    queryName: 'getTagsByRegex',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
