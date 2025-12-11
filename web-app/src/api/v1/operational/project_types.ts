import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'ProjectType'
const URL = '/v1/operational/project-types'

export type ProjectType = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getQueryParams = get['parameters']['query']

export const useGetProjectTypes = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const axiosConfig = {
    url: URL,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<ProjectType[]>({
    axiosConfig,
    queryName: 'getProjectTypes',
    pathParams: {},
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
