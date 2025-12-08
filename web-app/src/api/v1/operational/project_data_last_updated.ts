import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'ProjectDataLastUpdated'
const URL = '/v1/operational/project-data-last-updated/'

export type ProjectDataLastUpdated =
  types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']

export const useGetProjectDataLastUpdated = ({
  queryParams,
  queryOptions = {},
}: {
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    refetchInterval: 1000 * 30,
  }

  return useCustomQuery<ProjectDataLastUpdated[]>({
    axiosConfig,
    queryName: 'getProjectDataLastUpdated',
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
