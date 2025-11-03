import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

export enum ProjectTypeId {
  PV = 1,
  BESS = 2,
  PV_BESS = 3,
}

export interface ProjectType {
  project_type_id: ProjectTypeId
  name_short: string
  name_long: string
}

export const useGetProjectTypes = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: {
    project_type_ids?: ProjectTypeId[]
    name_short?: string
    name_long?: string
  }
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const axiosConfig = {
    url: '/v1/operational/project-types/',
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
