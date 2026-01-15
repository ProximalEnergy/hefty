import type * as types from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const _COMPONENT_NAME = 'CompanyProject'
const URL = '/v1/admin/company-projects/projects/{project_id}/all-companies'

type CompanyProject = types.components['schemas'][typeof _COMPONENT_NAME]
type get = types.paths[typeof URL]['get']
type getPathParams = get['parameters']['path']

export const useGetAllCompanyProjectsForProject = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: getPathParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  }

  return useCustomQuery<CompanyProject[]>({
    axiosConfig,
    queryName: 'getAllCompanyProjectsForProject',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
