import { ProjectDataLastUpdated } from '@/api/v1/operational/project_data_last_updated'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

export const useGetDataLastUpdated = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/data-last-updated`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    refetchInterval: QUERY_TIME.THIRTY_SECONDS,
  }

  return useCustomQuery<ProjectDataLastUpdated>({
    axiosConfig,
    queryName: 'getDataLastUpdated',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
