import * as generatedTypes from '@/api/_example/openapi-typescript/api-types'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

// Specify this once per hook
const URL = '/v1/operational/projects'

// All types are pulled in automatically for the given URL
type Project = generatedTypes.components['schemas']['Project']
type get = generatedTypes.paths[typeof URL]['get']
type getPathParams = get['parameters']['path']
type getQueryParams = get['parameters']['query']

export const useGetProjectsOpenAPITypeScript = ({
  pathParams = undefined,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams?: getPathParams
  queryParams: getQueryParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<Project[]>({
    axiosConfig,
    queryName: 'getProjectsOpenAPITypeScript',
    pathParams,
    queryParams,
    queryOptions,
  })
}
