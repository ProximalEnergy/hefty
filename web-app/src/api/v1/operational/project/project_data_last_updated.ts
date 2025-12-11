import { ProjectDataLastUpdated } from '@/api/v1/operational/project_data_last_updated'
import { useCustomQuery } from '@/hooks/api'
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

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    refetchInterval: 1000 * 30,
  }

  return useCustomQuery<ProjectDataLastUpdated>({
    axiosConfig,
    queryName: 'getDataLastUpdated',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
