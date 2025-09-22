import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export interface ProjectDataLastUpdated {
  project_id: string
  time_error: string | null
  time_empty: string | null
  time_last: string | null
}

export const useGetProjectDataLastUpdated = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams: { project_ids: string[] }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/project-data-last-updated/`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    refetchInterval: 1000 * 30,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<ProjectDataLastUpdated[]>({
    axiosConfig,
    queryName: 'getProjectDataLastUpdated',
    queryParams,
    queryOptions,
  })
}
