import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface CompanyProject {
  company_id: string
  project_id: string
  vector_store_id: string
}

export const useGetAllCompanyProjectsForProject = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { project_id: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/admin/company-projects/projects/${pathParams.project_id}/all-companies`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  }

  return useCustomQuery<CompanyProject[]>({
    axiosConfig,
    queryName: 'getAllCompanyProjectsForProject',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}
